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
fan = 24 

GPIO.setmode(GPIO.BCM)
GPIO.setup(door_lock, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(lamp_UVC, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(lamp_normal, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(fan, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(door_sensor, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setwarnings(False)

# Global variable
global state
state = "waiting"       #edit

global sterilization_time
sterilization_time = 0

global cancel_flag
cancel_flag = False

global sterilization_times
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
root.geometry("1024x600")
root.title("UVC Sterilization Cabinet")

# Status message
statusMessage = ctk.CTkLabel(root, text="Please open the Door to insert items...", font=("Arial", 40))
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
      
        camera_frame = ctk.CTkLabel(root, text="", fg_color="black")
        camera_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        pastime = time.time() # time current
        window_width = 1024
        window_height = 600
        
        while (time.time() - pastime) < 10:# 
            im = picam2.capture_array() 
            im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
            im_resized = cv2.resize(im, (window_width, window_height))
            
            # predict
            results = model.predict(im_resized)
            a = results[0].boxes.data  
            px = pd.DataFrame(a).astype("float")
            
            for index, row in px.iterrows(): 
                x1, y1, x2, y2 = map(int, row[:4])
                confidence = float(row[4])
                class_index = int(row[5])
                class_name = class_list[class_index]
                
                if confidence >= 0.5:  
                    detected_classes.add(class_name)
                    cv2.rectangle(im_resized, (x1, y1), (x2, y2), (0, 0, 255), 2) 
                    cvzone.putTextRect(im_resized, f'{class_name} ({confidence:.2f})', (x1, y1+10), 1, 1)
            
            img = Image.fromarray(im_resized)
            img_tk = ImageTk.PhotoImage(image=img)
            camera_frame.configure(image=img_tk)
            camera_frame.image = img_tk

            root.update()
        
        if detected_classes:
            time.sleep(10)
            picam2.stop()
            camera_frame.configure(image=None)  # Clear the frame from the GUI
            camera_frame.image = None
            camera_frame.place_forget()
        
            max_delay = max(sterilization_times.get(cls, 0) for cls in detected_classes) # find time max
            sterilization_time = max_delay
            sterilize(sterilization_time)
            root.update()
        else:
            cancelButton.place_forget()          #edit
            statusMessage.configure(text="No items detected. Please open the door to reset.", font=("Arial", 30))
            openButtonEject.place(relx=0.5, rely=0.5, anchor="center")
            root.update()
            
    global state
    state = "waiting"
    picam2.stop()
    camera_frame.configure(image=None)  # Clear the frame from the GUI
    camera_frame.image = None
    camera_frame.place_forget()

# function to start sterilization
time_label = ctk.CTkLabel(root,text="",font=("Arial",100),text_color="green")
time_label.pack(pady=20)


# function to start sterilization
def sterilize(sterilization_time):
    global cancel_flag
    cancel_flag = False  # Reset cancel flag before starting sterilization

    cancelButton.place(relx=0.5, rely=0.7, anchor="center")     #edit
    GPIO.output(lamp_normal, False)  # Turn off lamp normal
    GPIO.output(lamp_UVC, True)  # Turn on lamp UVC
    
    end_time = time.time() + sterilization_time
    interval = 1
    previous_time = time.time()

    while True:
        current_time = time.time()
        remaining_time = int(end_time - current_time)
            
        if remaining_time <= 0 or cancel_flag:
            break
        
        if current_time - previous_time >= interval:
            previous_time = current_time
                
            min = remaining_time // 60
            sec = remaining_time % 60
            time_format = f"{min:02}:{sec:02}"
            
            statusMessage.configure(text="Sterilizing")     #edit
            time_label.configure(text=f"{time_format}")
            root.update()

    GPIO.output(lamp_UVC, False)  # Turn off UVC lamp after sterilization or cancellation
    time_label.configure(text="")  # Clear the time label
    if cancel_flag:
        pass
    else:
        statusMessage.configure(text="Sterilization complete. Wait for the fan to work for 1 minute" , font=("Arial", 30)) #edit
        GPIO.output(fan, True)
        time.sleep(60)
        GPIO.output(fan, False)
        statusMessage.configure(text="Complete! You can open items" , font=("Arial", 30)) 

    cancelButton.place_forget()  # Hide cancel button
    openButtonEject.place(relx=0.5, rely=0.5, anchor="center")  # Show open button again  

    root.update()

# function to cancel sterilization
def cancel():
    statusMessage.configure(text="")    
    time_label.configure(text="")
    global cancel_flag
    cancel_flag = True  # Set cancel flag to True
    cancelButton.place_forget()  # Hide cancel button
    root.update()
    GPIO.output(lamp_UVC, False)  # Turn off UVC lamp immediately
    statusMessage.configure(text="Process canceled. Please open the door to get your items.")
    openButtonEject.place(relx=0.5, rely=0.5, anchor="center")
    root.update()

# function to open the door
def open():
    GPIO.output(lamp_normal, True)  # Turn on normal lamp
    GPIO.output(door_lock, True)  # Unlock the door
    statusMessage.configure(text="Door unlocked. Please insert items.")
    root.update()
    time.sleep(0.5)
    GPIO.output(door_lock, False)  # Lock the door again
    openButton.place_forget()
    startDetect.place_forget()
   
    global state
    state = "init"
    
def eject():
    time.sleep(1)
    openButtonEject.place_forget()
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
    startDetect.place_forget()
    openButton.place_forget()
    GPIO.output(lamp_normal, True)
    #statusMessage.configure(text="Initializing...")        #edit
    root.update
    global state
    state = "insert"

# Buttons
openButton = ctk.CTkButton(root, corner_radius=15, text="open", font=("Arail", 50, "bold"), fg_color="#6495ED", hover_color="#4d7fd9", height=100, width=220, command=open)
openButtonEject = ctk.CTkButton(root, corner_radius=15, text="Open", font=("Arail", 50, "bold"),fg_color="#6495ED", hover_color="#4d7fd9", height=100, width=220, command=eject)
cancelButton = ctk.CTkButton(root, corner_radius=15, text="Cancel", fg_color="#de3163", hover_color="#af204a", font=("Arail", 50, "bold"), height=100, width=220, command=cancel)
startDetect = ctk.CTkButton(root, corner_radius=15, text="Start", font=("Arail", 50, "bold"), fg_color="#18ad5f", hover_color="#119b53", height=100, width=220, command=detect)

openButton.place(relx=0.5, rely=0.5, anchor="center")

# Main Loop
while True:
    if state == "waiting":
        time.sleep(0.1)  # Waiting for door to be closed
        
    elif state == "init":
        while GPIO.input(door_sensor) == GPIO.HIGH:     #edit
            statusMessage.configure(text="")# Wait until door is closed
            time.sleep(0.1)
        statusMessage.configure(text="Open Door or Start Sterilize.")   #edit
        openButton.place(relx=0.35, rely=0.5, anchor="center")
        startDetect.place(relx=0.65, rely=0.5, anchor="center")
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