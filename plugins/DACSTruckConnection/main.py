"""
ETS2 Dynamic Truck Connection Plugin with Leader/Follower Dynamics
This plugin handles dynamic truck connections, leader/follower negotiations,
and integrates with ETS2LA for real-time position updates.
"""

from plugins.plugin import PluginInformation
from src.logger import print
import tkinter as tk
from tkinter import ttk
import src.settings as settings
import asyncio
import websockets
import json
import threading
import math
import uuid
import random

PluginInfo = PluginInformation(
    name="DACSTruckConnection",
    description="Handles dynamic truck connections with leader/follower dynamics.",
    version="0.4",
    author="SafwanChowdhury",
    url="https://github.com/SafwanChowdhury/Euro-Truck-Simulator-2-Lane-Assist",
    type="dynamic",
    dynamicOrder="last"
)

# Configuration
TRUCK_PORT = settings.GetSettings("DACSTruckConnection", "truck_port") or 39850
SERVER_PORT = settings.GetSettings("DACSTruckConnection", "server_port") or 39851
CONNECTION_RANGE = settings.GetSettings("DACSTruckConnection", "connection_range") or 300  # meters
IS_LEADER = settings.GetSettings("DACSTruckConnection", "is_leader") or False

class Truck:
    def __init__(self, id, websocket=None, is_leader=False):
        self.id = id
        self.websocket = websocket
        self.position = {"coordinateX": 0, "coordinateZ": 0}
        self.vector = {"velocityX": 0, "velocityZ": 0}
        self.connections = set()
        self.is_leader = is_leader
        self.leader = self if is_leader else None

    async def update_data(self, data):
        self.position = data.get("truckPlacement", self.position)
        self.vector = data.get("truckVector", self.vector)

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)

trucks = {}
current_truck = None
websocket_server = None
stop_event = None

async def handle_client(websocket, path):
    truck_id = str(uuid.uuid4())
    truck = Truck(truck_id, websocket)
    trucks[truck_id] = truck
    try:
        print(f"New truck connected: {truck_id}")
        await broadcast_truck_joined(truck)
        async for message in websocket:
            data = json.loads(message)
            await truck.update_data(data)
            await process_truck_data(truck)
    finally:
        del trucks[truck_id]
        await broadcast_truck_left(truck)
        print(f"Truck disconnected: {truck_id}")

async def broadcast_truck_joined(new_truck):
    message = json.dumps({"type": "truck_joined", "id": new_truck.id})
    await broadcast_to_all(message, exclude=new_truck)

async def broadcast_truck_left(left_truck):
    message = json.dumps({"type": "truck_left", "id": left_truck.id})
    await broadcast_to_all(message)

async def broadcast_to_all(message, exclude=None):
    for truck in trucks.values():
        if truck != exclude and truck.websocket:
            await truck.websocket.send(message)

async def process_truck_data(truck):
    for other_truck in trucks.values():
        if other_truck != truck:
            distance = calculate_distance(truck.position, other_truck.position)
            if distance <= CONNECTION_RANGE:
                if other_truck not in truck.connections:
                    truck.connections.add(other_truck)
                    other_truck.connections.add(truck)
                    await negotiate_leader_follower(truck, other_truck)
                    await notify_server(truck, other_truck)
            elif other_truck in truck.connections:
                truck.connections.remove(other_truck)
                other_truck.connections.remove(truck)
                await reset_leader_follower(truck, other_truck)

async def negotiate_leader_follower(truck1, truck2):
    if truck1.is_leader and truck2.is_leader:
        # If both are leaders or neither, randomly choose one
        new_leader = random.choice([truck1, truck2])
        new_follower = truck2 if new_leader == truck1 else truck1
        new_leader.is_leader = True
        new_follower.is_leader = False
        new_follower.leader = new_leader
    elif truck1.is_leader:
        truck2.leader = truck1
    elif truck2.is_leader:
        truck1.leader = truck2
    else:
        new_leader = random.choice([truck1, truck2])
        new_follower = truck2 if new_leader == truck1 else truck1
        new_leader.is_leader = True
        new_follower.leader = new_leader

    await update_leader_status(truck1)
    await update_leader_status(truck2)

async def reset_leader_follower(truck1, truck2):
    if truck1.leader == truck2:
        truck1.leader = None
    if truck2.leader == truck1:
        truck2.leader = None
    await update_leader_status(truck1)
    await update_leader_status(truck2)

async def update_leader_status(truck):
    if truck.websocket:
        message = json.dumps({
            "type": "leader_status_update",
            "is_leader": truck.is_leader,
            "leader_id": truck.leader.id if truck.leader else None
        })
        await truck.websocket.send(message)

async def notify_server(truck1, truck2):
    server_uri = f"ws://localhost:{SERVER_PORT}"
    async with websockets.connect(server_uri) as server_ws:
        message = json.dumps({
            "command": "launch_gbpplanner",
            "truck1": {"id": truck1.id, "position": truck1.position, "is_leader": truck1.is_leader},
            "truck2": {"id": truck2.id, "position": truck2.position, "is_leader": truck2.is_leader}
        })
        await server_ws.send(message)
    print(f"Notified server: Trucks {truck1.id} and {truck2.id} connected")

def calculate_distance(pos1, pos2):
    return math.sqrt((pos1["coordinateX"] - pos2["coordinateX"])**2 + 
                     (pos1["coordinateZ"] - pos2["coordinateZ"])**2)

async def start_server():
    global websocket_server, stop_event
    stop_event = asyncio.Event()
    websocket_server = await websockets.serve(handle_client, "0.0.0.0", TRUCK_PORT)
    print(f"Websocket server started on 0.0.0.0:{TRUCK_PORT}")
    await stop_event.wait()

def run_server():
    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(start_server())
    finally:
        loop.close()

async def send_current_truck_data():
    global current_truck
    if current_truck and current_truck.websocket:
        data = {
            "truckPlacement": current_truck.position,
            "truckVector": current_truck.vector
        }
        await current_truck.websocket.send(json.dumps(data))

def onEnable():
    global server_task, current_truck
    server_task = threading.Thread(target=run_server)
    server_task.start()
    current_truck = Truck("current_truck", is_leader=IS_LEADER)
    trucks[current_truck.id] = current_truck

def onDisable():
    global stop_event, websocket_server, server_task, current_truck
    if stop_event:
        asyncio.run(stop_event.set())
    if websocket_server:
        websocket_server.close()
    if server_task and server_task.is_alive():
        server_task.join(timeout=5)
    if current_truck:
        del trucks[current_truck.id]
        current_truck = None

def plugin(data):
    global current_truck
    if "GPS" in data and "api" in data:
        current_truck.position = {
            "coordinateX": data["GPS"].get("x", 0.0),
            "coordinateZ": data["GPS"].get("z", 0.0)
        }
        current_truck.vector = {
            "velocityX": data["api"]["truckVector"].get("lv_accelerationX", 0.0),
            "velocityZ": data["api"]["truckVector"].get("lv_accelerationZ", 0.0)
        }
        asyncio.run(send_current_truck_data())
    return data

class UI():
    def __init__(self, master):
        self.master = master
        self.create_ui()

    def create_ui(self):
        self.root = tk.Canvas(self.master, width=600, height=520, border=0, highlightthickness=0)
        self.root.grid_propagate(0)
        self.root.pack_propagate(0)

        ttk.Label(self.root, text="ETS2 Dynamic Truck Connection Plugin").grid(row=0, column=0, padx=5, pady=5)
        ttk.Label(self.root, text=f"Truck server port: {TRUCK_PORT}").grid(row=1, column=0, padx=5, pady=5)
        ttk.Label(self.root, text=f"GBP Planner server port: {SERVER_PORT}").grid(row=2, column=0, padx=5, pady=5)
        ttk.Label(self.root, text=f"Connection range: {CONNECTION_RANGE} meters").grid(row=3, column=0, padx=5, pady=5)
        ttk.Label(self.root, text=f"Initial leader status: {'Leader' if IS_LEADER else 'Follower'}").grid(row=4, column=0, padx=5, pady=5)

        self.truck_count_label = ttk.Label(self.root, text="Connected trucks: 0")
        self.truck_count_label.grid(row=5, column=0, padx=5, pady=5)

        self.position_label = ttk.Label(self.root, text="Current Position: (0, 0)")
        self.position_label.grid(row=6, column=0, padx=5, pady=5)

        self.leader_status_label = ttk.Label(self.root, text="Leader Status: N/A")
        self.leader_status_label.grid(row=7, column=0, padx=5, pady=5)

        self.root.pack(anchor="center", expand=False)

    def destroy(self):
        self.root.destroy()

    def update(self, data):
        self.truck_count_label.config(text=f"Connected trucks: {len(trucks)}")
        if current_truck:
            self.position_label.config(text=f"Current Position: ({current_truck.position['coordinateX']:.2f}, {current_truck.position['coordinateZ']:.2f})")
            leader_status = "Leader" if current_truck.is_leader else f"Follower (Leader: {current_truck.leader.id if current_truck.leader else 'None'})"
            self.leader_status_label.config(text=f"Leader Status: {leader_status}")
        self.root.update()