import RPi.GPIO as GPIO
from time import sleep
import customtkinter as ctk
import cv2
from picamera2 import Picamera2
import pandas as pd
from ultralytics import YOLO
import cvzone
from PIL import Image, ImageTk

class UVCSterilizationApp:
    def __init__(self, root):
        # GPIO setup
        self.door_sensor = 23
        self.door_lock = 16
        self.lamp_UVC = 17
        self.lamp_normal = 27

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.door_lock, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(self.lamp_UVC, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(self.lamp_normal, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(self.door_sensor, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setwarnings(False)

        # Variables
        self.state = "insert"
        self.sterilization_time = 0
        self.detected_classes = set()
        self.sterilization_times = {
            "box": 10,
            "coin": 15,
            "glass": 16,
            "mask": 9,
            "sandals": 11,
            "sock": 8,
            "spoon": 12
        }

        # GUI setup
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        root.geometry("750x450")
        root.title("UVC Sterilization Cabinet")

        self.statusMessage = ctk.CTkLabel(root, text="Initializing...", font=("Arial", 16))
        self.statusMessage.pack(pady=20)

        self.startButton = ctk.CTkButton(root, text="Start", fg_color="green", command=self.start)
        self.cancelButton = ctk.CTkButton(root, text="Cancel", fg_color="red", command=self.cancel)
        self.openButton = ctk.CTkButton(root, text="Open", fg_color="blue", command=self.open)
        self.camera_frame = ctk.CTkLabel(root)

        self.openButton.pack(pady=10)
        self.root = root

        # Initialize YOLO model
        self.model = YOLO('/home/pi/YOLO/NCNN/adam-100-epochs/best_ncnn_model', task="segment")
        with open("/home/pi/YOLO/coco.txt", "r") as my_file:
            self.class_list = my_file.read().splitlines()

    def start(self):
        self.startButton.pack_forget()
        GPIO.output(self.lamp_normal, False)
        GPIO.output(self.lamp_UVC, True)

        for remaining_time in range(self.sterilization_time, 0, -1):
            self.statusMessage.configure(text=f"Time remaining: {remaining_time} seconds.")
            self.root.update()
            sleep(1)

        GPIO.output(self.lamp_UVC, False)
        self.statusMessage.configure(text="Sterilization complete. You can open the door now.")
        self.openButton.pack(pady=10)

    def cancel(self):
        GPIO.output(self.lamp_UVC, False)
        GPIO.output(self.lamp_normal, True)
        self.statusMessage.configure(text="Process canceled. Please open the door to reset.")
        self.openButton.pack(pady=10)

    def open(self):
        GPIO.output(self.lamp_normal, True)
        GPIO.output(self.door_lock, True)
        self.statusMessage.configure(text="Door unlocked. Please insert items.")
        sleep(0.5)
        GPIO.output(self.door_lock, False)

    def detect_objects(self):
        self.statusMessage.configure(text="Detecting items...")
        self.camera_frame.pack(pady=10)

        with Picamera2() as picam2:
            picam2.start()

            while not self.detected_classes:
                im = picam2.capture_array()
                im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
                img_tk = ImageTk.PhotoImage(image=Image.fromarray(im))
                self.camera_frame.configure(image=img_tk)
                self.camera_frame.image = img_tk
                self.root.update()

                results = self.model.predict(im)
                for result in results[0].boxes.data:
                    x1, y1, x2, y2, conf, cls = map(float, result)
                    if conf >= 0.5:
                        self.detected_classes.add(self.class_list[int(cls)])
                        cv2.rectangle(im, (int(x1), int(y1)), (int(x2), int(y2)), (0, 0, 255), 2)

                img_tk = ImageTk.PhotoImage(image=Image.fromarray(im))
                self.camera_frame.configure(image=img_tk)
                self.camera_frame.image = img_tk

            picam2.stop()
            self.camera_frame.configure(image=None)
            self.camera_frame.image = None

        self.sterilization_time = max(self.sterilization_times.get(cls, 0) for cls in self.detected_classes)
        self.statusMessage.configure(text=f"Objects detected: {', '.join(self.detected_classes)}")
        self.startButton.pack(pady=10)
        self.cancelButton.pack(pady=10)

    def cleanup(self):
        GPIO.cleanup()

# Main execution
if __name__ == "__main__":
    root = ctk.CTk()
    app = UVCSterilizationApp(root)
    try:
        root.mainloop()
    finally:
        app.cleanup()