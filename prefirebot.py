import customtkinter as ctk
from tkinter import Toplevel, Canvas, Frame, Scrollbar, Menu
from PIL import ImageGrab, ImageTk, Image
import pyautogui
import numpy as np
import time
import threading
from pynput import keyboard
import json

class ColorMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Color Monitor")
        self.root.geometry("500x600")

        self.green_hp_color = None
        self.yellow_hp_color = None
        self.threshold = 10  # Default threshold
        self.monitoring = False
        self.selected_key = None
        self.region_width = 200  # Initial width of the detection region

        self.load_colors()

        # Create UI elements
        self.select_green_color_btn = ctk.CTkButton(root, text="Select Green HP Color", command=self.select_green_color)
        self.select_green_color_btn.pack(pady=10)

        self.select_yellow_color_btn = ctk.CTkButton(root, text="Select Yellow HP Color", command=self.select_yellow_color)
        self.select_yellow_color_btn.pack(pady=10)

        self.threshold_label = ctk.CTkLabel(root, text="Detection Threshold (1-10):")
        self.threshold_label.pack(pady=5)

        self.threshold_slider = ctk.CTkSlider(root, from_=1, to=10, number_of_steps=9, command=self.update_threshold)
        self.threshold_slider.set(self.threshold)
        self.threshold_slider.pack(pady=5)

        self.select_key_btn = ctk.CTkButton(root, text="Select Key to Hold", command=self.select_key)
        self.select_key_btn.pack(pady=10)

        self.region_canvas = Canvas(root, width=self.region_width, height=100, bg="white", highlightthickness=1, highlightbackground="black")
        self.region_canvas.pack(pady=10)

        self.green_color_label = ctk.CTkLabel(root, text="Green HP Color: Not selected")
        self.green_color_label.pack(pady=10)

        self.yellow_color_label = ctk.CTkLabel(root, text="Yellow HP Color: Not selected")
        self.yellow_color_label.pack(pady=10)

        self.key_label = ctk.CTkLabel(root, text="Selected Key: None")
        self.key_label.pack(pady=10)

        if self.green_hp_color:
            green_color_name = self.get_color_name(self.green_hp_color)
            self.green_color_label.configure(text=f"Green HP Color: {green_color_name}")

        if self.yellow_hp_color:
            yellow_color_name = self.get_color_name(self.yellow_hp_color)
            self.yellow_color_label.configure(text=f"Yellow HP Color: {yellow_color_name}")

        if self.selected_key:
            self.key_label.configure(text=f"Selected Key: {self.selected_key}")

        self.instruction_label = None

        self.listener = keyboard.Listener(on_press=self.on_key_press, on_release=self.on_key_release)
        self.listener.start()

        self.root.bind("<F1>", self.log_monitoring_status)

        # Add menu for increasing region width
        self.create_menu()

        # Bind mouse events for region resizing
        self.setup_region_resizing()

    def update_threshold(self, value):
        self.threshold = int(value)
        print(f"Threshold set to: {self.threshold}")

    def select_green_color(self):
        self.pick_color("Select the green HP color.", self.set_green_hp_color)

    def select_yellow_color(self):
        self.pick_color("Select the yellow/orange HP color.", self.set_yellow_hp_color)

    def set_green_hp_color(self, color):
        self.green_hp_color = color
        self.save_colors()
        if self.green_hp_color:
            green_color_name = self.get_color_name(self.green_hp_color)
            self.green_color_label.configure(text=f"Green HP Color: {green_color_name}")

    def set_yellow_hp_color(self, color):
        self.yellow_hp_color = color
        self.save_colors()
        if self.yellow_hp_color:
            yellow_color_name = self.get_color_name(self.yellow_hp_color)
            self.yellow_color_label.configure(text=f"Yellow HP Color: {yellow_color_name}")

    def pick_color(self, message, callback):
        self.show_instruction(message)
        zoom_window = Toplevel(self.root)
        zoom_window.geometry("200x200")
        zoom_window.overrideredirect(1)
        zoom_canvas = Canvas(zoom_window, width=200, height=200)
        zoom_canvas.pack()

        def update_zoom():
            x, y = pyautogui.position()
            bbox = (x - 10, y - 10, x + 10, y + 10)
            img = ImageGrab.grab(bbox=bbox)
            img = img.resize((200, 200), Image.NEAREST)
            imgtk = ImageTk.PhotoImage(img)
            zoom_canvas.create_image(0, 0, anchor='nw', image=imgtk)
            zoom_window.imgtk = imgtk
            zoom_window.after(10, update_zoom)

        def capture_zoomed_area(event):
            if event.keysym == "Return":
                x, y = pyautogui.position()
                bbox = (x - 10, y - 10, x + 10, y + 10)
                img = ImageGrab.grab(bbox=bbox)
                zoom_window.destroy()
                self.pick_color_from_zoomed_area(img, callback)

        zoom_window.bind("<Key>", capture_zoomed_area)
        zoom_window.focus_set()
        update_zoom()

    def pick_color_from_zoomed_area(self, img, callback):
        unique_colors = list(set(img.getdata()))
        self.show_color_list(unique_colors, callback)

    def show_color_list(self, colors, callback):
        color_list_window = Toplevel(self.root)
        color_list_window.geometry("200x300")

        frame = Frame(color_list_window)
        frame.pack(fill="both", expand=True)

        scrollbar = Scrollbar(frame, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        color_listbox = Canvas(frame, yscrollcommand=scrollbar.set)
        color_listbox.pack(side="left", fill="both", expand=True)

        scrollbar.config(command=color_listbox.yview)

        for color in colors:
            color_frame = Frame(color_listbox, bg=self.color_to_hex(color), width=200, height=20)
            color_frame.pack_propagate(False)
            color_frame.pack(fill="x")

            def select_color(event, selected_color=color):
                print(f"Color selected: {selected_color}")
                self.clear_instruction()
                color_list_window.destroy()
                callback(selected_color)

            color_frame.bind("<Button-1>", select_color)

        color_listbox.update_idletasks()
        color_listbox.config(scrollregion=color_listbox.bbox("all"))

    def show_instruction(self, message):
        self.clear_instruction()
        self.instruction_label = ctk.CTkLabel(self.root, text=message)
        self.instruction_label.pack(pady=5)

    def clear_instruction(self):
        if self.instruction_label:
            self.instruction_label.destroy()

    def color_to_hex(self, color):
        return f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"

    def color_present(self, target_color, region):
        im = ImageGrab.grab(bbox=region)
        im_np = np.array(im)
        color_diff = np.abs(im_np - target_color)
        matches = np.all(color_diff <= self.threshold, axis=-1)
        return np.any(matches)

    def start_monitoring(self):
        if self.green_hp_color and self.yellow_hp_color and self.selected_key:
            self.monitoring = True
            monitoring_thread = threading.Thread(target=self.monitor_color_change)
            monitoring_thread.start()
        else:
            print("Please select both colors and a key before starting.")

    def monitor_color_change(self):
        screen_width, screen_height = pyautogui.size()
        left_region = (0, screen_height // 2 - 50, self.region_width, screen_height // 2 + 50)
        right_region = (screen_width - self.region_width, screen_height // 2 - 50, screen_width, screen_height // 2 + 50)
        print("Monitoring screen for color change in the center...")

        yellow_logged = False
        while self.monitoring:
            yellow_detected_left = self.color_present(self.yellow_hp_color, left_region)
            yellow_detected_right = self.color_present(self.yellow_hp_color, right_region)

            if yellow_detected_left or yellow_detected_right:
                yellow_logged = True

            if not yellow_detected_left and not yellow_detected_right and yellow_logged:
                print("Yellow/Orange HP disappeared from view! Performing left click.")
                pyautogui.mouseDown(button='left')  # Mouse down for left click
                pyautogui.mouseUp(button='left')  # Mouse up for left click
                time.sleep(0.1)  # Optional delay after click

            time.sleep(0.1)

    def increase_region_width(self):
        self.region_width += 50  # Increase the region width by 50 pixels
        print(f"Region width increased to: {self.region_width}")
        self.update_region_box()

    def update_region_box(self):
        self.region_canvas.config(width=self.region_width)
        self.region_canvas.update()

    def create_menu(self):
        self.menu = Menu(self.root)
        self.root.config(menu=self.menu)

        self.region_menu = Menu(self.menu, tearoff=0)
        self.menu.add_cascade(label="Region", menu=self.region_menu)
        self.region_menu.add_command(label="Increase Width", command=self.increase_region_width)

    def setup_region_resizing(self):
        self.region_canvas.bind("<ButtonPress-1>", self.on_start_resize)
        self.region_canvas.bind("<B1-Motion>", self.on_resize)

        self.left_resize_handle = self.region_canvas.create_rectangle(0, 0, 5, 100, fill="black", tags="resize_handle")
        self.right_resize_handle = self.region_canvas.create_rectangle(self.region_width - 5, 0, self.region_width, 100, fill="black", tags="resize_handle")

    def on_start_resize(self, event):
        self.resize_handle = event.widget.find_closest(event.x, event.y)[0]
        self.start_x = event.x

    def on_resize(self, event):
        if self.resize_handle == self.left_resize_handle:
            self.region_width = max(50, self.region_width - (event.x - self.start_x))
            self.start_x = event.x
        elif self.resize_handle == self.right_resize_handle:
            self.region_width = max(50, self.region_width + (event.x - self.start_x))
            self.start_x = event.x

        self.update_region_box()

    def select_key(self):
        print("Press a key to hold:")
        self.show_instruction("Press a key to hold:")
        self.selected_key = None

    def on_key_press(self, key):
        try:
            self.selected_key = key.char
            self.key_label.configure(text=f"Selected Key: {self.selected_key}")
            self.clear_instruction()
            if key.char == self.selected_key:
                self.monitoring = True
                print(f"Started monitoring on key press: {key.char}")
                self.monitor_color_change()
        except AttributeError:
            pass

    def on_key_release(self, key):
        try:
            if key.char == self.selected_key:
                self.monitoring = False
                print(f"Stopped monitoring on key release: {key.char}")
        except AttributeError:
            pass

    def log_monitoring_status(self, event):
        print(f"Monitoring status: {'ON' if self.monitoring else 'OFF'}")

    def load_colors(self):
        try:
            with open("colors.json", "r") as f:
                colors = json.load(f)
                self.green_hp_color = tuple(colors["green_hp_color"])
                self.yellow_hp_color = tuple(colors["yellow_hp_color"])
        except FileNotFoundError:
            print("No previous color data found.")

    def save_colors(self):
        colors = {
            "green_hp_color": self.green_hp_color,
            "yellow_hp_color": self.yellow_hp_color,
        }
        with open("colors.json", "w") as f:
            json.dump(colors, f)

    def get_color_name(self, color):
        # Replace this with a function that maps colors to names or labels
        return "Custom Color"

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    app = ColorMonitorApp(root)
    root.mainloop()
