import RPi.GPIO as GPIO
from time import sleep
import customtkinter as ctk
import cv2
from picamera2 import Picamera2  # ใช้ควบคุมกล้อง Pi
import pandas as pd 
from ultralytics import YOLO
import cvzone
import numpy as np
import builtins
from PIL import Image, ImageTk

# GPIO setup
door_sensor = 23  
door_lock = 16     
lamp_UVC = 17      
lamp_normal = 27    

GPIO.setmode(GPIO.BCM)
GPIO.setup(door_lock, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(lamp_UVC, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(lamp_normal, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(door_sensor, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setwarnings(False)

# Global variable
global state
state = "insert"
global sterilization_time
sterilization_time = 0
global sterilization_times

sterilization_times = {  # เวลาฆ่าเชื้อสำหรับวัตถุต่างๆ
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
root = ctk.CTk()
root.geometry("750x450")
root.title("UVC Sterilization Cabinet")

# Status message
statusMessage = ctk.CTkLabel(root, text="Initializing...", font=("Arial", 16))
statusMessage.pack(pady=20)

detected_classes = set()

# function to detect objects with PiCamera2 and YOLO
def detect_objects():
    # สร้าง object ของ Picamera2 และเริ่มการทำงานของกล้อง
    with Picamera2() as picam2:
        picam2.start()
        model = YOLO('/home/pi/YOLO/NCNN/adam-100-epochs/best_ncnn_model', task="segment")  # โหลดโมเดลสำหรับการ segment
        my_file = builtins.open("/home/pi/YOLO/coco.txt", "r")  # ชื่อของคลาส
        data = my_file.read()
        class_list = data.split("\n")  # เก็บข้อมูลชื่อคลาสในแต่ละบรรทัด
        
        # สร้าง label สำหรับแสดงภาพจากกล้องใน GUI
        camera_frame = ctk.CTkLabel(root)
        camera_frame.pack(pady=10)
        
        while not detected_classes:  # ลูปอ่านภาพจากกล้องและตรวจจับทุกๆ 3 เฟรม
            im = picam2.capture_array()  # ดึงข้อมูลภาพจากกล้อง
            im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)  # แปลงภาพเป็น RGB
            
            # แปลงภาพเป็นรูปแบบที่ Tkinter รองรับ
            img = Image.fromarray(im)
            img_tk = ImageTk.PhotoImage(image=img)
            
            # อัพเดทภาพใน label ของ Tkinter
            camera_frame.configure(image=img_tk)
            camera_frame.image = img_tk
            root.update()
        
            # ทำนายวัตถุจากโมเดล
            results = model.predict(im)
            a = results[0].boxes.data  # รับข้อมูลจากกรอบที่ตรวจพบ
            px = pd.DataFrame(a).astype("float")  # แปลงข้อมูลให้เป็น float และใส่ใน DataFrame
            
            for index, row in px.iterrows():  # วนลูปข้อมูลของกรอบที่ตรวจพบ
                x1, y1, x2, y2 = map(int, row[:4])
                confidence = float(row[4])
                class_index = int(row[5])
                class_name = class_list[class_index]
                
                if confidence >= 0.5:  # หากความมั่นใจสูงกว่า 50%
                    detected_classes.add(class_name)
                    cv2.rectangle(im, (x1, y1), (x2, y2), (0, 0, 255), 2)  # วาดกรอบ
                    cvzone.putTextRect(im, f'{class_name} ({confidence:.2f})', (x1, y1), 1, 1)  # แสดงชื่อและความมั่นใจ
                    
            # แปลงภาพที่แก้ไขแล้วเป็นรูปแบบที่ Tkinter รองรับ
            img = Image.fromarray(im)
            img_tk = ImageTk.PhotoImage(image=img)
            
        picam2.stop()  # หยุดการทำงานของกล้อง
        camera_frame.configure(image=None)  # ลบภาพจาก label
        camera_frame.image = None
        
        if detected_classes: 
            # คำนวณเวลาการฆ่าเชื้อโดยใช้เวลาสูงสุดจากการตรวจพบ
            max_delay = max(sterilization_times.get(cls, 0) for cls in detected_classes)
            sterilization_time = max_delay
            
            statusMessage.configure(text=f"Objects detected: {', '.join(detected_classes)}")
            root.update()

            statusMessage.configure(text=f"Sterilization time: {sterilization_time} seconds.")
            root.update()

            # แสดงปุ่ม Start และ Cancel
            startButton.pack(pady=10)
            cancelButton.pack(pady=10)
        else:
            statusMessage.configure(text="No items detected. Please open the door to reset.")
            root.update()
            state = "waiting"
            
    detected_classes.clear()  # เคลียร์คลาสที่ตรวจพบก่อนจะทำงานในรอบถัดไป
    root.update()

# function to start sterilization
def start():
    startButton.pack_forget()  # Hide start button again
    GPIO.output(lamp_normal, False)  # Turn off lamp normal
    GPIO.output(lamp_UVC, True)  # Turn on lamp UVC

    for remaining_time in range(sterilization_time, 0, -1):
        statusMessage.configure(text=f"Time remaining: {remaining_time} seconds.")
        root.update()
        sleep(1)

    GPIO.output(lamp_UVC, False)  # Turn off UVC lamp after sterilization is done 
    statusMessage.configure(text="Sterilization complete. You can open the door now.")
    root.update()
    cancelButton.pack_forget()  # Hide cancel button
    openButton.pack(pady=10)  # Show open button again 

# function to cancel sterilization
def cancel(): 
    startButton.pack_forget()  # Hide start button
    cancelButton.pack_forget()  # Hide cancel button 
    GPIO.output(lamp_UVC, False)
    GPIO.output(lamp_normal, True)  # Turn on normal lamp
    statusMessage.configure(text="Process canceled. Please open the door to reset.")
    root.update()
    openButton.pack(pady=10)  # Show open button again 
    global state
    state = "waiting"

# function to open the door
def open(): 
    GPIO.output(lamp_normal, True)  # Turn on normal lamp
    GPIO.output(door_lock, True)  # Unlock the door
    statusMessage.configure(text="Door unlocked. Please insert items.")
    root.update()
    sleep(0.5)
    GPIO.output(door_lock, False)  # Lock the door again
    openButton.pack_forget()  # Hide open button
    global state
    state = "open"

# Buttons 
openButton = ctk.CTkButton(root, text="Open", fg_color="blue", command=open)
startButton = ctk.CTkButton(root, text="Start", fg_color="green", command=start)
cancelButton = ctk.CTkButton(root, text="Cancel", fg_color="red", command=cancel)

# Main Loop
while True:
    if state == "waiting": sleep(0.1)  # Waiting for door to be closed
            
    elif state == "open":
        sleep(1)
        while GPIO.input(door_sensor) == GPIO.HIGH:  # Wait until door is closed
            statusMessage.configure(text="Close the door to detect...")
            root.update()
            sleep(0.1)
        statusMessage.configure(text="Door is closed. Detecting items...")
        root.update()
        sleep(1)
        state = "insert"

    elif state == "insert":
        statusMessage.configure(text="Door is closed. Detecting items...")
        root.update()
        sleep(1)
        detect_objects()

    detected_classes.clear()
    root.update()

# Clean up GPIO on exit
GPIO.cleanup()