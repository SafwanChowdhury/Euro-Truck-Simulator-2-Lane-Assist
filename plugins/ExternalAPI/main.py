"""
This is an example of a plugin (type="dynamic"), they will be updated during the stated point in the mainloop.
If you need to make a panel that is only updated when it's open then check the Panel example!
"""


from plugins.plugin import PluginInformation
from src.logger import print


PluginInfo = PluginInformation(
    name="ExternalAPI", # This needs to match the folder name under plugins (this would mean plugins\Plugin\main.py)
    description="Will post the application data to\nlocalhost:39847\nUsed for external applications.",
    version="0.1",
    author="Tumppi066",
    url="https://github.com/Tumppi066/Euro-Truck-Simulator-2-Lane-Assist",
    type="dynamic", # = Panel
    dynamicOrder="last" # Will run the plugin before anything else in the mainloop (data will be empty)
)

import threading
import tkinter as tk
from tkinter import ttk
import src.settings as settings
import json
import asyncio
import websockets
import numpy as np
import base64
import hashlib
from src.logger import print

port = settings.GetSettings("ExternalAPI", "port")
if port is None:
    settings.CreateSettings("ExternalAPI", "port", 39847)
    port = 39847

currentData = {}
server = None
server_task = None
stop_event = None

def convert_ndarrays(obj):
    if isinstance(obj, np.ndarray):
        return "ndarray not supported"
    elif isinstance(obj, dict):
        return {key: convert_ndarrays(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_ndarrays(value) for value in obj]
    else:
        return obj

async def websocket_handler(websocket, path):
    global currentData, stop_event
    print(f"New connection from {websocket.remote_address}")
    try:
        while not stop_event.is_set():
            try:
                await websocket.send(json.dumps(currentData))
                await asyncio.sleep(0.1)  # 10fps
            except websockets.exceptions.ConnectionClosed:
                break
    finally:
        print(f"Connection closed for {websocket.remote_address}")
        await websocket.close()

def generate_accept_key(key):
    GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    hash = hashlib.sha1((key + GUID).encode()).digest()
    return base64.b64encode(hash).decode()

async def start_server():
    global server, stop_event
    stop_event = asyncio.Event()
    server = await websockets.serve(
        websocket_handler, 
        "0.0.0.0", 
        port, 
        process_request=process_request
    )
    print(f"WebSocket server started on ws://0.0.0.0:{port}")
    await stop_event.wait()

async def process_request(path, headers):
    if "Sec-WebSocket-Key" in headers:
        key = headers["Sec-WebSocket-Key"]
        accept_key = generate_accept_key(key)
        return {
            "status": 101,
            "headers": [
                ("Upgrade", "websocket"),
                ("Connection", "Upgrade"),
                ("Sec-WebSocket-Accept", accept_key),
            ]
        }

def run_server():
    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_server())

def plugin(data):
    global currentData
    tempData = {}
    for key in data:
        if key == "frame" or key == "frameFull":
            tempData[key] = "too large to send"
            continue
        
        if key == "GPS":
            from plugins.Map.GameData.roads import RoadToJson
            tempData[key] = data[key]
            tempData[key]["roads"] = [RoadToJson(road) for road in data[key]["roads"]]
            continue
        
        tempData[key] = data[key]

    currentData = convert_ndarrays(tempData)
    return data

def onEnable():
    global server_task
    if server_task is None or not server_task.is_alive():
        server_task = threading.Thread(target=run_server)
        server_task.start()
    else:
        print("WebSocket server is already running")

def onDisable():
    global stop_event, server, server_task
    if stop_event:
        asyncio.run(stop_event.set())
    if server:
        server.close()
    if server_task and server_task.is_alive():
        server_task.join()
    print("WebSocket server stopped")

class UI():
    try: # The panel is in a try loop so that the logger can log errors if they occur
        
        def __init__(self, master) -> None:
            self.master = master # "master" is the mainUI window
            self.exampleFunction()
        
        def destroy(self):
            self.done = True
            self.root.destroy()
            del self

        
        def exampleFunction(self):
            
            try:
                self.root.destroy() # Load the UI each time this plugin is called
            except: pass
            
            self.root = tk.Canvas(self.master, width=600, height=520, border=0, highlightthickness=0)
            self.root.grid_propagate(0) # Don't fit the canvast to the widgets
            self.root.pack_propagate(0)

            def savenewport():
                print(self.newport.get())
                settings.CreateSettings("ExternalAPI", "port", self.newport.get())
            def validate_entry(text):
                # Make sure that only integers can be typed
                return text.isdecimal()

            ttk.Label(self.root, text="Port").grid(row=1, padx=5, pady=5)
            self.newport = tk.IntVar()
            ttk.Entry(self.root, validate="key", textvariable=self.newport,
    validatecommand=(self.root.register(validate_entry), "%S")).grid(row=2, padx=5, pady=5)
            ttk.Button(self.root, text="Save", command=savenewport).grid(row=3, padx=5, pady=5)

            ttk.button(self.root, text="button").grid()
            self.root.pack(anchor="center", expand=False)
            self.root.update()
        
        
        def update(self, data): # When the panel is open this function is called each frame 
            self.root.update()
    
    
    except Exception as ex:
        print(ex.args)
