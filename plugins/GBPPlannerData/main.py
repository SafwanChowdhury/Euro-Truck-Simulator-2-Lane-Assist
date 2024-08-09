from plugins.plugin import PluginInformation
import cv2
import numpy as np
import win32gui, win32con
from ctypes import windll, byref, c_int, sizeof
import tkinter as tk
from tkinter import ttk

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

        # Create an empty frame to draw on
        height_frame = 400
        width_frame = 800
        frame = np.zeros((height_frame, width_frame, 3), dtype=np.uint8)

        # Draw received data on the frame
        draw_text(frame, "Position:", 0.1, 0.2, received_position_x, received_position_y)
        draw_text(frame, "Velocity:", 0.1, 0.3, received_velocity_x, received_velocity_y)
        draw_text(frame, "Acceleration:", 0.1, 0.4, received_acceleration)
        draw_text(frame, "Turn Angle:", 0.1, 0.5, received_turn_angle)
        draw_text(frame, "Next Speed:", 0.1, 0.6, received_next_speed)

        # Show the frame in a window
        cv2.imshow(name_window, frame)

        # Handle window properties and resizing
        handle_window_properties(name_window)

    return data

# UI class to manage settings and display received data
class UI():
    def __init__(self, master) -> None:
        self.master = master 
        self.init_ui()
        self.master.after(1000, self.update_received_data)  # Update every second

    def init_ui(self):
        self.root = tk.Canvas(self.master, width=800, height=600, border=0, highlightthickness=0)
        self.root.pack_propagate(0)
        self.root.pack(anchor="center", expand=False)
        
        self.received_data_frame = ttk.Frame(self.root)
        self.received_data_frame.pack(fill="both", expand=True)

        self.position_label = ttk.Label(self.received_data_frame, text="Position: ")
        self.position_label.pack(anchor="w")

        self.velocity_label = ttk.Label(self.received_data_frame, text="Velocity: ")
        self.velocity_label.pack(anchor="w")

        self.acceleration_label = ttk.Label(self.received_data_frame, text="Acceleration: ")
        self.acceleration_label.pack(anchor="w")

        self.turn_angle_label = ttk.Label(self.received_data_frame, text="Turn Angle: ")
        self.turn_angle_label.pack(anchor="w")

        self.next_speed_label = ttk.Label(self.received_data_frame, text="Next Speed: ")
        self.next_speed_label.pack(anchor="w")

        ttk.Button(self.root, text="Save", command=self.save).pack(anchor="center", pady=6)

    def update_received_data(self):
        global data

        if "externalapi" in data:
            received_json = data["externalapi"]["receivedJSON"]

            # Update labels with the latest received data
            position_text = f"Position: ({received_json.get('position', {}).get('x', 0):.2f}, {received_json.get('position', {}).get('y', 0):.2f})"
            velocity_text = f"Velocity: ({received_json.get('velocity', {}).get('x', 0):.2f}, {received_json.get('velocity', {}).get('y', 0):.2f})"
            acceleration_text = f"Acceleration: {received_json.get('acceleration', 0):.2f}"
            turn_angle_text = f"Turn Angle: {received_json.get('turn_angle', 0):.2f}"
            next_speed_text = f"Next Speed: {received_json.get('next_speed', 0):.2f}"

            self.position_label.config(text=position_text)
            self.velocity_label.config(text=velocity_text)
            self.acceleration_label.config(text=acceleration_text)
            self.turn_angle_label.config(text=turn_angle_text)
            self.next_speed_label.config(text=next_speed_text)

        # Schedule the next update
        self.master.after(1000, self.update_received_data)
