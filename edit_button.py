import RPi.GPIO as GPIO
import time
import customtkinter as ctk
import cv2
from picamera2 import Picamera2  
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
state = "waiting"
global sterilization_time
sterilization_time = 0
global sterilization_times
global cancel_flag
cancel_flag = False

sterilization_times = {  
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
statusMessage = ctk.CTkLabel(root, text="Please open the Door to insert items...", font=("Arial", 16))
statusMessage.pack(pady=20)

detected_classes = set()

# function to detect objects with PiCamera2 and YOLO
def detect_objects():
    with Picamera2() as picam2:
        picam2.start()
        model = YOLO('/home/pi/YOLO/NCNN/adam-100-epochs/best_ncnn_model', task="segment")  
        my_file = builtins.open("/home/pi/YOLO/coco.txt", "r")
        data = my_file.read()
        class_list = data.split("\n") 
      
        camera_frame = ctk.CTkLabel(root)
        camera_frame.pack(pady=10)
        
        # time current
        pastime = time.time()
        
        while (time.time() - pastime) < 10:# 
            im = picam2.capture_array() 
            im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB) 
            
            img = Image.fromarray(im)
            img_tk = ImageTk.PhotoImage(image=img)
            
            camera_frame.configure(image=img_tk)
            camera_frame.image = img_tk
            root.update()
        
            results = model.predict(im)
            a = results[0].boxes.data  
            px = pd.DataFrame(a).astype("float")
            
            for index, row in px.iterrows(): 
                x1, y1, x2, y2 = map(int, row[:4])
                confidence = float(row[4])
                class_index = int(row[5])
                class_name = class_list[class_index]
                
                if confidence >= 0.5:  
                    detected_classes.add(class_name)
                    cv2.rectangle(im, (x1, y1), (x2, y2), (0, 0, 255), 2) 
                    cvzone.putTextRect(im, f'{class_name} ({confidence:.2f})', (x1, y1), 1, 1)
            
            if detected_classes:
                picam2.stop()  # Stop the camera after detection
                camera_frame.configure(image=None)  # Clear the frame from the GUI
                camera_frame.image = None
                camera_frame.pack_forget()
                break  # Exit the loop as objects are detected
            
            img = Image.fromarray(im)
            img_tk = ImageTk.PhotoImage(image=img)
        
        if detected_classes:
            max_delay = max(sterilization_times.get(cls, 0) for cls in detected_classes)
            sterilization_time = max_delay
            sterilize(sterilization_time)
            cancelButton.pack(pady=10)
            root.update()
        else:
            statusMessage.configure(text="No items detected. Please open the door to reset.")
            openButtonEject.pack(pady=10)
            root.update()
            
    global state
    state = "waiting"
    picam2.stop()
    camera_frame.configure(image=None)  # Clear the frame from the GUI
    camera_frame.image = None
    camera_frame.pack_forget()


# function to start sterilization
time_label = ctk.CTkLabel(root,text="",font=("Arial",100),text_color="green")
time_label.pack(pady=20)

# function to start sterilization
def sterilize(sterilization_time):
    global cancel_flag
    cancel_flag = False  # Reset cancel flag before starting sterilization

    GPIO.output(lamp_normal, False)  # Turn off lamp normal
    GPIO.output(lamp_UVC, True)  # Turn on lamp UVC

    for remaining_time in range(sterilization_time, 0, -1):
        if cancel_flag:  # Check if cancel flag is True
            break  # Exit the loop immediately

        min = remaining_time // 60
        sec = remaining_time % 60
        time_format = f"{min:02}:{sec:02}"

        statusMessage.configure(text="Time Sterilize")
        time_label.configure(text=f"{time_format}")
        root.update()
        time.sleep(1)

    GPIO.output(lamp_UVC, False)  # Turn off UVC lamp after sterilization or cancellation
    time_label.configure(text="")  # Clear the time label
    if cancel_flag:
        statusMessage.configure(text="Process canceled. Please open the door to reset.")
    else:
        statusMessage.configure(text="Sterilization complete. You can open the door now.")

    cancelButton.pack_forget()  # Hide cancel button
    openButtonEject.pack(pady=10)  # Show open button again  

    root.update()

# function to cancel sterilization
def cancel():
    global cancel_flag
    cancel_flag = True  # Set cancel flag to True
    GPIO.output(lamp_UVC, False)  # Turn off UVC lamp immediately
    statusMessage.configure(text="Process canceled. Please open the door to reset.")
    root.update()
    cancelButton.pack_forget()  # Hide cancel button
    openButtonEject.pack(pady=10)  # Show open button again
ัดพักเดกเ้ด
# function to open the door
def open(): 
    GPIO.output(lamp_normal, True)  # Turn on normal lamp
    GPIO.output(door_lock, True)  # Unlock the door
    statusMessage.configure(text="Door unlocked. Please insert items.")
    root.update()
    time.sleep(0.5)
    GPIO.output(door_lock, False)  # Lock the door again
    openButton.pack_forget()
    startDetect.pack_forget()
    
    global state
    state = "init"
    
def eject():
    openButtonEject.pack_forget()
    GPIO.output(lamp_normal, True)  # Turn on normal lamp
    GPIO.output(door_lock, True)  # Unlock the door
    statusMessage.configure(text="Door unlocked. Please move your items.")
    root.update()
    time.sleep(0.5)

    GPIO.output(door_lock, False)  # Lock the door again
    time.sleep(5)
    GPIO.output(lamp_normal, False) # Turn on normal lamp
    global state
    state = "init"
    
def detect():
    startDetect.pack_forget()
    openButton.pack_forget()
    statusMessage.configure(text="Initializing...")
    root.update
    global state
    state = "insert"

# Buttons 
openButton = ctk.CTkButton(root, text="open", fg_color="blue", command=open)
openButtonEject = ctk.CTkButton(root, text="Open", fg_color="blue", command=eject)
startSterilization = ctk.CTkButton(root, text="Sterilize", fg_color="green", command=sterilize)
cancelButton = ctk.CTkButton(root, text="Cancel", fg_color="red", command=cancel)
startDetect = ctk.CTkButton(root, text="Start", fg_color="blue", command=detect)

openButton.pack(pady=10) 

# Main Loop
while True:
    if state == "waiting":
        time.sleep(0.1)  # Waiting for door to be closed
        
    elif state == "init":
        while GPIO.input(door_sensor) == GPIO.HIGH:
            statusMessage.configure(text="")# Wait until door is closed
            time.sleep(0.1)
            
        openButton.pack(pady=10)
        startDetect.pack(pady=10)
        root.update()

    elif state == "insert":
        statusMessage.configure(text="Door is closed. Detecting items...")
        root.update()
        time.sleep(1)
        detect_objects()
        
        root.update()
        time.sleep(1)

    detected_classes.clear()
    root.update()

# Clean up GPIO on exit
GPIO.cleanup()