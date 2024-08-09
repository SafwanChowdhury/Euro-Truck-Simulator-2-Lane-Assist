from plugins.plugin import PluginInformation
import cv2
import numpy as np
import win32gui, win32con
from ctypes import windll, byref, c_int, sizeof
import tkinter as tk
from tkinter import ttk
import src.helpers as helpers
import src.settings as settings
from src.translator import Translate

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
width_frame = 800
height_frame = 400
last_width_frame = width_frame
last_height_frame = height_frame
frame_original = np.zeros((height_frame, width_frame, 3), dtype=np.uint8)

def LoadSettings():
    global width_frame, height_frame, last_width_frame, last_height_frame, frame_original
    width_frame = settings.GetSettings("GBPPlannerData", "width_frame", 800)
    height_frame = settings.GetSettings("GBPPlannerData", "height_frame", 400)
    last_width_frame = width_frame
    last_height_frame = height_frame
    frame_original = np.zeros((height_frame, width_frame, 3), dtype=np.uint8)

# Helper function to draw text on the frame
def draw_text(frame, label, x_pos, y_pos, *values):
    current_text = f"{label} {', '.join(f'{value:.2f}' for value in values)}"
    fontscale = 1
    thickness = 2

    textsize, _ = cv2.getTextSize(current_text, cv2.FONT_HERSHEY_SIMPLEX, fontscale, thickness)
    width, height = textsize

    cv2.putText(frame, current_text, (round(x_pos * frame.shape[1]), round(y_pos * frame.shape[0] + height / 2)),
                cv2.FONT_HERSHEY_SIMPLEX, fontscale, text_color, thickness)

# Helper function to handle window properties and resizing
def handle_window_properties(window_name):
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    hwnd = win32gui.FindWindow(None, window_name)
    windll.dwmapi.DwmSetWindowAttribute(hwnd, 35, byref(c_int(0x000000)), sizeof(c_int))

def plugin(data):
    global width_frame, height_frame, last_width_frame, last_height_frame, frame_original

    # Check if external data is available
    if "externalapi" in data:
        received_json = data["externalapi"]["receivedJSON"]

        # Extract relevant data from received_json
        received_position_x = received_json.get('position', {}).get('x', 0)
        received_position_y = received_json.get('position', {}).get('y', 0)
        received_velocity_x = received_json.get('velocity', {}).get('x', 0)
        received_velocity_y = received_json.get('velocity', {}).get('y', 0)
        received_acceleration = received_json.get('acceleration', 0)
        received_turn_angle = received_json.get('turn_angle', 0)
        received_next_speed = received_json.get('next_speed', 0)

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

        # Draw received data on the frame
        draw_text(frame, "Position:", 0.1, 0.2, received_position_x, received_position_y)
        draw_text(frame, "Velocity:", 0.1, 0.3, received_velocity_x, received_velocity_y)
        draw_text(frame, "Acceleration:", 0.1, 0.4, received_acceleration)
        draw_text(frame, "Turn Angle:", 0.1, 0.5, received_turn_angle)
        draw_text(frame, "Next Speed:", 0.1, 0.6, received_next_speed)

        # Show the frame in a window
        cv2.imshow(name_window, frame)

        # Handle window properties and resizing
        if resize_frame:
            handle_window_properties(name_window)

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