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
    fontscale = 1
    thickness = 2

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
    print(data)
    if "externalapi" in data:
        received_json = data["externalapi"]["receivedJSON"]

        position_x = received_json.get('position', {}).get('x', 0)
        position_y = received_json.get('position', {}).get('y', 0)
        velocity_x = received_json.get('velocity', {}).get('x', 0)
        velocity_y = received_json.get('velocity', {}).get('y', 0)
        acceleration = received_json.get('acceleration', 0)
        turn_angle = received_json.get('turn_angle', 0)
        next_speed = received_json.get('next_speed', 0)

        draw_text(frame, "Position X:", 0.1, 0.2, position_x)
        draw_text(frame, "Position Y:", 0.1, 0.3, position_y)
        draw_text(frame, "Velocity X:", 0.1, 0.4, velocity_x)
        draw_text(frame, "Velocity Y:", 0.1, 0.5, velocity_y)
        draw_text(frame, "Acceleration:", 0.1, 0.6, acceleration)
        draw_text(frame, "Turn Angle:", 0.1, 0.7, turn_angle)
        draw_text(frame, "Next Speed:", 0.1, 0.8, next_speed)

    else:
        cv2.putText(frame, "Waiting for GBPPlanner data...", (int(0.1*width_frame), int(0.5*height_frame)),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, text_color, 2)

    cv2.imshow(name_window, frame)

    if resize_frame:
        cv2.resizeWindow(name_window, width_frame, height_frame)
        handle_window_properties(name_window)
    else:
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