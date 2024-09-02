from plugins.plugin import PluginInformation
import cv2
import numpy as np
import win32gui, win32con
from ctypes import windll, byref, c_int, sizeof
import tkinter as tk
from tkinter import ttk
import src.helpers as helpers
import src.settings as settings
import src.variables as variables
from src.translator import Translate
import time
import pyautogui

PluginInfo = PluginInformation(
    name="GBPPlannerData",
    description="This Plugin shows some statistics from GBPPlanner",
    version="0.1",
    author="SafwanChowdhury",
    url="https://github.com/SafwanChowdhury/Euro-Truck-Simulator-2-Lane-Assist",
    type="dynamic", 
    dynamicOrder="before game",
    requires=["ExternalAPI-Socket"]
)

# Constants
name_window = "GBPPlanner Data"
text_color = (255, 255, 255)

# Global variables
width_screen, height_screen = pyautogui.size()
width_frame = settings.GetSettings("GBPPlannerData", "width_frame", round(height_screen/2.5))
height_frame = settings.GetSettings("GBPPlannerData", "height_frame", round(height_screen/4))
last_width_frame = width_frame
last_height_frame = height_frame
frame_original = np.zeros((height_frame, width_frame, 3), dtype=np.uint8)

def LoadSettings():
    global width_frame, height_frame, last_width_frame, last_height_frame, frame_original
    width_frame = settings.GetSettings("GBPPlannerData", "width_frame", round(height_screen/2.5))
    height_frame = settings.GetSettings("GBPPlannerData", "height_frame", round(height_screen/4))
    last_width_frame = width_frame
    last_height_frame = height_frame
    frame_original = np.zeros((height_frame, width_frame, 3), dtype=np.uint8)

def draw_text(frame, label, x_pos, y_pos, value):
    current_text = f"{label} {value:.2f}"
    max_width = int(frame.shape[1] * 0.9)  # 90% of frame width
    max_height = int(frame.shape[0] * 0.1)  # 10% of frame height
    fontscale = get_optimal_font_scale(current_text, max_width, max_height)
    thickness = 2

    textsize, _ = cv2.getTextSize(current_text, cv2.FONT_HERSHEY_SIMPLEX, fontscale, thickness)
    width, height = textsize

    cv2.putText(frame, current_text, (round(x_pos * frame.shape[1]), round(y_pos * frame.shape[0] + height / 2)),
                cv2.FONT_HERSHEY_SIMPLEX, fontscale, text_color, thickness)

def get_optimal_font_scale(text, max_width, max_height):
    fontScale = 1
    thickness = 2
    while True:
        textSize = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, fontScale, thickness)[0]
        if textSize[0] > max_width or textSize[1] > max_height:
            fontScale -= 0.1
        else:
            return fontScale

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

def mpsToMPH(speed):
    return speed * 2.23694  # Convert m/s to mph

def plugin(data):
    global width_frame, height_frame, last_width_frame, last_height_frame, frame_original

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
            settings.CreateSettings("GBPPlannerData", "width_frame", width_frame)
            settings.CreateSettings("GBPPlannerData", "height_frame", height_frame)

    last_width_frame, last_height_frame = width_frame, height_frame

    frame = frame_original.copy()

    if "last" in data and "externalapi" in data["last"] and "receivedJSON" in data["last"]["externalapi"]:
        received_json = data["last"]["externalapi"]["receivedJSON"]
        host_id = data["last"]["externalapi"].get("host_id")
        
        # Ensure received_json is not None and is a dictionary
        if received_json and isinstance(received_json, dict):
            # Check if the host_id matches
            if received_json.get('host_id') == host_id:
                position = received_json.get('position', {})
                position_x = position.get('x', 0)
                position_y = position.get('y', 0)
                acceleration = mpsToMPH(received_json.get('acceleration', 0))
                next_speed = received_json.get('next_speed', 0)
                override_cruise_control = received_json.get('override_cruise_control', False)

                draw_text(frame, "Position X:", 0.1, 0.2, position_x)
                draw_text(frame, "Position Y:", 0.1, 0.3, position_y)
                draw_text(frame, "Acceleration (mph/s):", 0.1, 0.4, acceleration)
                draw_text(frame, "Next Speed (mph):", 0.1, 0.5, next_speed)
                draw_text(frame, "Override Cruise Control:", 0.1, 0.6, override_cruise_control)
            else:
                cv2.putText(frame, "Received data is not for this host", (int(0.1*width_frame), int(0.5*height_frame)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 1)
            
            # Display other trucks' data
            other_trucks_data = data["last"]["externalapi"].get("otherTrucksData", [])
            num_trucks = len(other_trucks_data)
            y_offset = 0.7 if num_trucks == 0 else 0.6

            # Get the current truck's position
            current_position = received_json.get('position', {})
            current_x = current_position.get('x', 0)
            current_y = current_position.get('y', 0)

            for truck in other_trucks_data:
                truck_id = truck.get('robot_id')
                position = truck.get('position', {})
                
                truck_x = position.get('x', 0)
                truck_y = position.get('y', 0)

                # Calculate the distance between the current truck and this truck
                distance = ((truck_x - current_x)**2 + (truck_y - current_y)**2)**0.5

                draw_text(frame, f"Truck ID {truck_id} - Distance:", 0.1, y_offset, distance)
                y_offset += min(0.1, 0.3 / max(1, num_trucks))  # Adjust spacing based on number of trucks
                
                # Remove the following lines as we don't need them anymore
                # if y_offset > 0.9:
                #     y_offset = 0.1
            
        else:
            cv2.putText(frame, "Received data is not in the expected format", (int(0.1*width_frame), int(0.5*height_frame)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 1)
    else:
        max_width = int(frame.shape[1] * 0.9)
        max_height = int(frame.shape[0] * 0.1)
        waiting_text = "Waiting for GBPPlanner data..."
        fontscale = get_optimal_font_scale(waiting_text, max_width, max_height)
        cv2.putText(frame, waiting_text, (int(0.1*width_frame), int(0.5*height_frame)),
                    cv2.FONT_HERSHEY_SIMPLEX, fontscale, text_color, 2)

    cv2.imshow(name_window, frame)

    if resize_frame:
        cv2.resizeWindow(name_window, width_frame, height_frame)
        handle_window_properties(name_window)
    else:
        # Ensure the window stays on top even when not resizing
        hwnd = win32gui.FindWindow(None, name_window)
        win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, 
                            win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)

    cv2.setWindowProperty(name_window, cv2.WND_PROP_TOPMOST, 1)

    return data


def onEnable():
    LoadSettings()

def onDisable():
    cv2.destroyAllWindows()

class UI():
    def __init__(self, master):
        self.master = master
        self.init_ui()

    def init_ui(self):
        self.root = tk.Canvas(self.master, width=800, height=600, border=0, highlightthickness=0)
        self.root.pack_propagate(0)
        self.root.pack(anchor="center", expand=False)
        
        self.frame = ttk.Frame(self.root)
        self.frame.pack(fill="both", expand=True)

        helpers.MakeLabel(self.frame, "GBPPlanner Data Settings", 0, 0, font=("Robot", 12, "bold"), columnspan=3)
        helpers.MakeEmptyLine(self.frame, 1, 0)

        ttk.Button(self.root, text="Save", command=self.save).pack(anchor="center", pady=6)

    def save(self):
        LoadSettings()

    def tabFocused(self):
        pass

    def update(self, data):
        self.root.update()

    def destroy(self):
        self.root.destroy()
        del self