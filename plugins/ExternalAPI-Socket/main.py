"""
This is an example of a plugin (type="dynamic"), they will be updated during the stated point in the mainloop.
If you need to make a panel that is only updated when it's open then check the Panel example!
"""


from plugins.plugin import PluginInformation
from src.logger import print

PluginInfo = PluginInformation(
    name="ExternalAPI-Socket", # This needs to match the folder name under plugins (this would mean plugins\Plugin\main.py)
    description="Will send application data to connected client over websockets. Used for external applications.",
    version="0.1",
    author="Tumppi066 & SafwanChowdhury",
    url="https://github.com/SafwanChowdhury/Euro-Truck-Simulator-2-Lane-Assist",
    type="dynamic", # = Panel
    dynamicOrder="last" # Will run the plugin before anything else in the mainloop (data will be empty)
)

import tkinter as tk
from tkinter import ttk
import src.settings as settings
import threading
import numpy as np
import json
import asyncio
import uuid

port = 39846

currentData = {}
received_json = {}
other_trucks_data = {}
server = None
server_task = None
stop_event = None
host_id = str(uuid.uuid4())


def convert_ndarrays(obj):
    if isinstance(obj, np.ndarray):
        return "ndarray not supported"
    elif isinstance(obj, dict):
        return {key: convert_ndarrays(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_ndarrays(value) for value in obj]
    else:
        return obj

async def handle_client(reader, writer):
    global currentData, stop_event
    addr = writer.get_extra_info('peername')
    print(f"New connection from {addr}")
    try:
        send_task = asyncio.create_task(send_data(writer))
        receive_task = asyncio.create_task(receive_data(reader))
        await asyncio.gather(send_task, receive_task)
    finally:
        print(f"Connection closed for {addr}")
        writer.close()
        await writer.wait_closed()

async def send_data(writer):
    global currentData, stop_event, host_id
    try:
        while not stop_event.is_set():
            message = json.dumps({**currentData, "host_id": host_id})
            writer.write(message.encode() + b'\n')
            await writer.drain()
            await asyncio.sleep(0.033)  # 30 FPS
    except Exception as e:
        print(f"Error sending data: {e}")

async def receive_data(reader):
    global stop_event, received_json, other_trucks_data, host_id
    try:
        while not stop_event.is_set():
            data = await reader.readline()
            if not data:
                break
            message = data.decode().strip()
            try:
                json_data = json.loads(message)
                if 'iteration_data' in json_data and 'all_trucks_data' in json_data:
                    # Extract own iteration data
                    if json_data['iteration_data']['host_id'] == host_id:
                        received_json = json_data['iteration_data']
                    
                    # Extract data of other trucks
                    other_trucks_data = [truck for truck in json_data['all_trucks_data'] if truck['host_id'] != host_id]
                else:
                    print(f"Unexpected data structure: {json_data}")
            except json.JSONDecodeError:
                print(f"Error decoding JSON: {message}")
            except KeyError as e:
                print(f"Missing key in JSON data: {e}")
    except Exception as e:
        print(f"Error receiving data: {e}")

async def start_server():
    global server, stop_event
    stop_event = asyncio.Event()
    try:
        server = await asyncio.start_server(handle_client, '0.0.0.0', port, reuse_address=True)
        print(f"Server started on 0.0.0.0:{port}")
        async with server:
            await stop_event.wait()
    except OSError as e:
        print(f"Error starting server: {e}")
        print("Try changing the port in the settings if this persists.")

def run_server():
    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(start_server())
    except Exception as e:
        print(f"Error in run_server: {e}")
    finally:
        loop.close()

def onEnable():
    global server_task
    if server_task is None or not server_task.is_alive():
        server_task = threading.Thread(target=run_server)
        server_task.start()
    else:
        print("Server is already running")

def onDisable():
    global stop_event, server, server_task
    if stop_event:
        asyncio.run(stop_event.set())
    if server:
        server.close()
    if server_task and server_task.is_alive():
        server_task.join(timeout=5)  # Wait up to 5 seconds for the thread to finish
        if server_task.is_alive():
            print("Warning: Server thread did not stop cleanly")
    print("Server stopped")

def plugin(data):
    global currentData, received_json, other_trucks_data, host_id
    tempData = {
        "api": {
            "truckPlacement": {
                "coordinateX": 0.0,
                "coordinateZ": 0.0
            },
            "truckVector": {
                "velocityX": 0.0,
                "velocityZ": 0.0
            }
        },
        "host_id": host_id
    }
    
    for key in data:
        if key == "frame" or key == "frameFull":
            continue
        
        if key == "GPS":
            from plugins.Map.GameData.roads import RoadToJson
            tempData["api"]["truckPlacement"]["coordinateX"] = data[key].get("x", 0.0)
            tempData["api"]["truckPlacement"]["coordinateZ"] = data[key].get("z", 0.0)
            tempData["api"]["roads"] = [RoadToJson(road) for road in data[key].get("roads", [])]
            continue
        
        if key == "api":
            if "truckPlacement" in data[key]:
                tempData["api"]["truckPlacement"]["coordinateX"] = data[key]["truckPlacement"].get("coordinateX", 0.0)
                tempData["api"]["truckPlacement"]["coordinateZ"] = data[key]["truckPlacement"].get("coordinateZ", 0.0)
            if "truckVector" in data[key]:
                tempData["api"]["truckVector"]["velocityX"] = data[key]["truckVector"].get("lv_accelerationX", 0.0)
                tempData["api"]["truckVector"]["velocityZ"] = data[key]["truckVector"].get("lv_accelerationZ", 0.0)
            continue
        
        tempData[key] = convert_ndarrays(data[key])
    
    currentData = tempData
    data["externalapi"] = {}
    data["externalapi"]["receivedJSON"] = received_json
    data["externalapi"]["otherTrucksData"] = other_trucks_data
    data["externalapi"]["host_id"] = host_id
    return data

    return data

class UI():
    try:
        def __init__(self, master) -> None:
            self.master = master
            self.exampleFunction()
        
        def destroy(self):
            self.done = True
            self.root.destroy()
            del self
        
        def exampleFunction(self):
            try:
                self.root.destroy()
            except:
                pass
            
            self.root = tk.Canvas(self.master, width=600, height=520, border=0, highlightthickness=0)
            self.root.grid_propagate(0)
            self.root.pack_propagate(0)

            def save_ports():
                settings.CreateSettings("ExternalAPI-Socket", "send_port", self.send_port.get())
                settings.CreateSettings("ExternalAPI-Socket", "receive_port", self.receive_port.get())
                print(f"Send Port: {self.send_port.get()}, Receive Port: {self.receive_port.get()}")

            def validate_entry(text):
                return text.isdecimal()

            ttk.Label(self.root, text="Send Port").grid(row=1, padx=5, pady=5)
            self.send_port = tk.IntVar(value=SEND_PORT)
            ttk.Entry(self.root, validate="key", textvariable=self.send_port,
                validatecommand=(self.root.register(validate_entry), "%S")).grid(row=2, padx=5, pady=5)

            ttk.Label(self.root, text="Receive Port").grid(row=3, padx=5, pady=5)
            self.receive_port = tk.IntVar(value=RECEIVE_PORT)
            ttk.Entry(self.root, validate="key", textvariable=self.receive_port,
                validatecommand=(self.root.register(validate_entry), "%S")).grid(row=4, padx=5, pady=5)

            ttk.Button(self.root, text="Save", command=save_ports).grid(row=5, padx=5, pady=5)

            self.root.pack(anchor="center", expand=False)
            self.root.update()
        
        def update(self, data):
            self.root.update()
    
    except Exception as ex:
        print(ex.args)