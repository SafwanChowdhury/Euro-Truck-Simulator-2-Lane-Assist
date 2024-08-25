"""
ETS2 Dynamic Truck Connection Plugin with Leader/Follower Dynamics and Real-time Data Display
This plugin handles dynamic truck connections, leader/follower negotiations,
integrates with ETS2LA for real-time position updates, and displays data in a pop-up window.
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
import pyautogui

PluginInfo = PluginInformation(
    name="DACSTruckConnection",
    description="Handles dynamic truck connections with leader/follower dynamics and real-time data display.",
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

# OpenCV window constants
name_window = "DACSTruckConnection Data"
text_color = (255, 255, 255)

# Global variables
width_screen, height_screen = pyautogui.size()
width_frame = settings.GetSettings("DACSTruckConnection", "width_frame", round(height_screen/2.5))
height_frame = settings.GetSettings("DACSTruckConnection", "height_frame", round(height_screen/4))
last_width_frame = width_frame
last_height_frame = height_frame
frame_original = np.zeros((height_frame, width_frame, 3), dtype=np.uint8)

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

trucks = {}
current_truck = None
websocket_server = None
stop_event = None

def LoadSettings():
    global width_frame, height_frame, last_width_frame, last_height_frame, frame_original
    width_frame = settings.GetSettings("DACSTruckConnection", "width_frame", round(height_screen/2.5))
    height_frame = settings.GetSettings("DACSTruckConnection", "height_frame", round(height_screen/4))
    last_width_frame = width_frame
    last_height_frame = height_frame
    frame_original = np.zeros((height_frame, width_frame, 3), dtype=np.uint8)

def draw_text(frame, label, x_pos, y_pos, value):
    current_text = f"{label} {value}"
    fontscale = 0.7
    thickness = 1

    textsize, _ = cv2.getTextSize(current_text, cv2.FONT_HERSHEY_SIMPLEX, fontscale, thickness)
    width, height = textsize

    cv2.putText(frame, current_text, (round(x_pos * frame.shape[1]), round(y_pos * frame.shape[0] + height / 2)),
                cv2.FONT_HERSHEY_SIMPLEX, fontscale, text_color, thickness)

def handle_window_properties(window_name):
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    hwnd = win32gui.FindWindow(None, window_name)

    win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, 
                          win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
    
    windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, byref(c_int(0x000000)), sizeof(c_int))

    icon_flags = win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE
    hicon = win32gui.LoadImage(None, f"{variables.PATH}assets/favicon.ico", win32con.IMAGE_ICON, 0, 0, icon_flags)

    win32gui.SendMessage(hwnd, win32con.WM_SETICON, win32con.ICON_SMALL, hicon)
    win32gui.SendMessage(hwnd, win32con.WM_SETICON, win32con.ICON_BIG, hicon)

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

async def update_ui():
    global width_frame, height_frame, last_width_frame, last_height_frame, frame_original

    while True:
        try:
            size_frame = cv2.getWindowImageRect(name_window)
            width_frame, height_frame = size_frame[2], size_frame[3]
            resize_frame = False
        except:
            width_frame, height_frame = last_width_frame, last_height_frame
            resize_frame = True

        if width_frame != last_width_frame or height_frame != last_height_frame:
            if width_frame >= 50 and height_frame >= 50:
                frame_original = np.zeros((height_frame, width_frame, 3), dtype=np.uint8)
                settings.CreateSettings("DACSTruckConnection", "width_frame", width_frame)
                settings.CreateSettings("DACSTruckConnection", "height_frame", height_frame)

        last_width_frame, last_height_frame = width_frame, height_frame

        frame = frame_original.copy()

        draw_text(frame, "Connected trucks:", 0.1, 0.1, len(trucks))
        if current_truck:
            draw_text(frame, "Current Position X:", 0.1, 0.2, f"{current_truck.position['coordinateX']:.2f}")
            draw_text(frame, "Current Position Z:", 0.1, 0.3, f"{current_truck.position['coordinateZ']:.2f}")
            draw_text(frame, "Velocity X:", 0.1, 0.4, f"{current_truck.vector['velocityX']:.2f}")
            draw_text(frame, "Velocity Z:", 0.1, 0.5, f"{current_truck.vector['velocityZ']:.2f}")
            draw_text(frame, "Leader Status:", 0.1, 0.6, "Leader" if current_truck.is_leader else "Follower")
            if current_truck.leader and not current_truck.is_leader:
                draw_text(frame, "Leader ID:", 0.1, 0.7, current_truck.leader.id)
        else:
            draw_text(frame, "No current truck data", 0.1, 0.2, "")

        cv2.imshow(name_window, frame)

        if resize_frame:
            cv2.resizeWindow(name_window, width_frame, height_frame)
            handle_window_properties(name_window)
        else:
            hwnd = win32gui.FindWindow(None, name_window)
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, 
                                  win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)

        cv2.setWindowProperty(name_window, cv2.WND_PROP_TOPMOST, 1)

        await asyncio.sleep(1/30)  # Update at 30 FPS

def change_leader_status(is_leader):
    global current_truck
    if current_truck:
        current_truck.is_leader = is_leader
        current_truck.leader = current_truck if is_leader else None
        asyncio.create_task(update_leader_status(current_truck))
        settings.CreateSettings("DACSTruckConnection", "is_leader", is_leader)
        print(f"Changed leader status to: {'Leader' if is_leader else 'Follower'}")

def onEnable():
    global server_task, current_truck
    LoadSettings()
    server_task = threading.Thread(target=run_server)
    server_task.start()
    current_truck = Truck("current_truck", is_leader=IS_LEADER)
    trucks[current_truck.id] = current_truck
    asyncio.create_task(update_ui())

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
        asyncio.create_task(process_truck_data(current_truck))
    return data

class UI():
    def __init__(self, master):
        self.master = master
        self.create_ui()

    def create_ui(self):
        self.root = tk.Canvas(self.master, width=600, height=520, border=0, highlightthickness=0)
        self.root.grid_propagate(0)
        self.root.pack_propagate(0)

        ttk.Label(self.root, text="DACSTruckConnection Settings").grid(row=0, column=0, padx=5, pady=5)
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

        self.root.pack(anchor="center", expand=False)

    def on_leader_checkbox_change(self):
        is_leader = self.is_leader_var.get()
        change_leader_status(is_leader)

    def destroy(self):
        self.root.destroy()

    def update(self, data):
        self.root.update()