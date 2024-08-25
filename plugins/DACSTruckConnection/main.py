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
import cv2
import numpy as np
import win32gui, win32con
from ctypes import windll, byref, c_int, sizeof
import socket

PluginInfo = PluginInformation(
    name="DACSTruckConnection",
    description="Handles dynamic truck connections with leader/follower dynamics.",
    version="0.5",
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

# Global variables
trucks = {}
current_truck = None
websocket_server = None
stop_event = None
window_name = "DACS Truck Connection"
frame = None
server_running = False

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
        if not isinstance(other, Truck):
            return False
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)

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
        if truck is not exclude and truck.websocket:
            try:
                await truck.websocket.send(message)
            except websockets.exceptions.WebSocketException:
                print(f"Failed to send message to truck {truck.id}. Websocket might be closed.")

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
        new_leader = truck1 if truck1.id < truck2.id else truck2
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
        try:
            message = json.dumps({
                "type": "leader_status_update",
                "is_leader": truck.is_leader,
                "leader_id": truck.leader.id if truck.leader else None
            })
            await truck.websocket.send(message)
        except websockets.exceptions.WebSocketException:
            print(f"Failed to update leader status for truck {truck.id}. Websocket might be closed.")
    
    await broadcast_to_all(json.dumps({
        "type": "truck_status_change",
        "truck_id": truck.id,
        "is_leader": truck.is_leader
    }), exclude=truck)

async def notify_server(truck1, truck2):
    server_uri = f"ws://localhost:{SERVER_PORT}"
    try:
        async with websockets.connect(server_uri) as server_ws:
            message = json.dumps({
                "command": "launch_gbpplanner",
                "truck1": {"id": truck1.id, "position": truck1.position, "is_leader": truck1.is_leader},
                "truck2": {"id": truck2.id, "position": truck2.position, "is_leader": truck2.is_leader}
            })
            await server_ws.send(message)
        print(f"Notified server: Trucks {truck1.id} and {truck2.id} connected")
    except websockets.exceptions.WebSocketException:
        print(f"Failed to notify server about connection between trucks {truck1.id} and {truck2.id}")

def calculate_distance(pos1, pos2):
    return math.sqrt((pos1["coordinateX"] - pos2["coordinateX"])**2 + 
                     (pos1["coordinateZ"] - pos2["coordinateZ"])**2)

async def start_server():
    global websocket_server, stop_event, server_running
    if server_running:
        print("Server is already running")
        return
    
    stop_event = asyncio.Event()
    try:
        websocket_server = await websockets.serve(handle_client, "0.0.0.0", TRUCK_PORT)
        server_running = True
        print(f"Websocket server started on 0.0.0.0:{TRUCK_PORT}")
        await stop_event.wait()
    except Exception as e:
        print(f"Error starting server: {e}")
        print(f"Error details: {type(e).__name__}, {str(e)}")
        server_running = False

def run_server():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(start_server())
    except Exception as e:
        print(f"Error in run_server: {e}")
        print(f"Error details: {type(e).__name__}, {str(e)}")
    finally:
        loop.close()

def check_port_availability(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    return result != 0


async def send_current_truck_data():
    global current_truck
    if current_truck and current_truck.websocket:
        data = {
            "truckPlacement": current_truck.position,
            "truckVector": current_truck.vector
        }
        try:
            await current_truck.websocket.send(json.dumps(data))
        except websockets.exceptions.WebSocketException:
            print(f"Failed to send current truck data. Websocket might be closed.")

def change_leader_status(is_leader):
    global current_truck
    if current_truck:
        current_truck.is_leader = is_leader
        current_truck.leader = current_truck if is_leader else None
        asyncio.create_task(update_leader_status(current_truck))
        settings.CreateSettings("DACSTruckConnection", "is_leader", is_leader)
        print(f"Changed leader status to: {'Leader' if is_leader else 'Follower'}")

def create_window():
    global window_name, frame
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 400, 300)
    frame = np.zeros((300, 400, 3), dtype=np.uint8)

    hwnd = win32gui.FindWindow(None, window_name)
    win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, 
                          win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
    
    windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, byref(c_int(0x000000)), sizeof(c_int))

def update_window():
    global frame, current_truck, trucks
    frame.fill(0)

    # Display current truck info
    if current_truck:
        cv2.putText(frame, f"Current Truck ID: {current_truck.id[:8]}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, f"Position: ({current_truck.position['coordinateX']:.2f}, {current_truck.position['coordinateZ']:.2f})", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, f"Is Leader: {current_truck.is_leader}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        if current_truck.leader:
            cv2.putText(frame, f"Leader: {current_truck.leader.id[:8]}", (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    # Display connected trucks
    y_offset = 150
    cv2.putText(frame, f"Connected Trucks: {len(trucks)}", (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    for i, truck in enumerate(trucks.values()):
        if i > 4:  # Limit to 5 trucks to avoid overflow
            break
        y_offset += 30
        cv2.putText(frame, f"ID: {truck.id[:8]}, Leader: {truck.is_leader}", (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    cv2.imshow(window_name, frame)
    cv2.waitKey(1)

def onEnable():
    global server_task, current_truck
    if not server_running:
        if check_port_availability(TRUCK_PORT):
            server_task = threading.Thread(target=run_server)
            server_task.start()
        else:
            print(f"Port {TRUCK_PORT} is already in use. Cannot start the server.")
    current_truck = Truck("current_truck", is_leader=IS_LEADER)
    trucks[current_truck.id] = current_truck
    create_window()

def onDisable():
    global stop_event, websocket_server, server_task, current_truck, server_running
    if stop_event:
        asyncio.run(stop_event.set())
    if websocket_server:
        websocket_server.close()
    if server_task and server_task.is_alive():
        server_task.join(timeout=5)
    if current_truck:
        del trucks[current_truck.id]
        current_truck = None
    server_running = False
    cv2.destroyAllWindows()

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
        asyncio.create_task(send_current_truck_data())
    update_window()
    return data

class UI():
    def __init__(self, master):
        self.master = master
        self.create_ui()

    def create_ui(self):
        self.root = tk.Canvas(self.master, width=400, height=300, border=0, highlightthickness=0)
        self.root.pack(anchor="center", expand=False)

        ttk.Label(self.root, text="DACS Truck Connection Plugin").grid(row=0, column=0, padx=5, pady=5)
        ttk.Label(self.root, text=f"Truck server port: {TRUCK_PORT}").grid(row=1, column=0, padx=5, pady=5)
        ttk.Label(self.root, text=f"GBP Planner server port: {SERVER_PORT}").grid(row=2, column=0, padx=5, pady=5)
        ttk.Label(self.root, text=f"Connection range: {CONNECTION_RANGE} meters").grid(row=3, column=0, padx=5, pady=5)

        self.is_leader_var = tk.BooleanVar(value=IS_LEADER)
        self.leader_checkbox = ttk.Checkbutton(
            self.root,
            text="Set as Leader",
            variable=self.is_leader_var,
            command=self.on_leader_checkbox_change
        )
        self.leader_checkbox.grid(row=4, column=0, padx=5, pady=5)

    def on_leader_checkbox_change(self):
        is_leader = self.is_leader_var.get()
        change_leader_status(is_leader)

    def destroy(self):
        self.root.destroy()

    def update(self, data):
        self.root.update()