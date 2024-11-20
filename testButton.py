import RPi.GPIO as GPIO
from time import sleep
import customtkinter as ctk
import cv2
from picamera2 import Picamera2  
import pandas as pd
from ultralytics import YOLO
import cvzone
import threading  # เพิ่มการใช้ threading เพื่อให้ GUI ไม่ถูกบล็อก

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

# GUI setup
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")
root = ctk.CTk()
root.geometry("750x450")
root.title("UVC Sterilization Cabinet")

# status message
status_label = ctk.CTkLabel(root, text="Initializing...", font=("Arial", 16))
status_label.pack(pady=20)

# time label
countdown_label = ctk.CTkLabel(root, text="", font=("Arial", 40), text_color="green")
countdown_label.pack(pady=20)

# time status
countdown_running = False
countdown_task = None

# time predict
time = None

# button
open_button = ctk.CTkButton(root, text="Open", fg_color="blue", command=lambda: open_door())
start_button = ctk.CTkButton(root, text="Start", fg_color="green", command=lambda: start_sterilization())
stop_button = ctk.CTkButton(root, text="Stop", fg_color="red", command=lambda: stop_sterilization())

# Function update status
def update_status(message):
    status_label.configure(text=message)
    root.update()

# Function Open door
def open_door():
    GPIO.output(door_lock, False)  # Unlock the door
    update_status("Door unlocked.")
    open_button.pack_forget()  # hide open button when door unlocked
    check_door_status()

# Function Check door status
def check_door_status():
    global time
    while GPIO.input(door_sensor) == 1:  # Door open
        update_status("Door is opened, Please insert packet and close the door.")
        root.update()
        sleep(0.5)
    
    # lamp normal ON
    GPIO.output(lamp_normal, True)  
    update_status("lamp_normal ON")

    # Predict item
    update_status("Door closed. Predicting item...") 
    time = predict_item()
    sleep(5)

    update_status(f"Predicted sterilization time: {time} seconds.")
    start_button.pack(pady=20)

# Function predict item
def predict_item():
    picam2 = Picamera2()
    picam2.preview_configuration.main.size = (840, 440)
    picam2.preview_configuration.main.format = "RGB888"
    picam2.preview_configuration.align()
    picam2.configure("preview")
    picam2.start()

    model = YOLO('/home/pi/YOLO/NCNN/adam-100-epochs/best_ncnn_model', task="segment")
    with open("/home/pi/YOLO/coco.txt", "r") as my_file:  # read each line file coco.txt
        class_list = my_file.read().split("\n")

    class_delays = {
        "box": 10,
        "coin": 15,
        "glass": 16,
        "mask": 9,
        "sandals": 11,
        "sock": 8,
        "spoon": 12
    }
    
    detected_classes = set() 

    while not detected_classes:
        im = picam2.capture_array()
        im = cv2.flip(im, -1)

        results = model.predict(im)
        detections = results[0].boxes.data
        px = pd.DataFrame(detections).astype("float")
        
        for index, row in px.iterrows():
            x1, y1, x2, y2 = map(int, row[:4])  
            confidence = float(row[4])         
            class_index = int(row[5])         
            class_name = class_list[class_index]  

            if confidence >= 0.5:
                detected_classes.add(class_name)  
                cv2.rectangle(im, (x1, y1), (x2, y2), (0, 0, 255), 2)
                cvzone.putTextRect(im, f"{class_name} ({confidence:.2f})", (x1, y1), 1, 1)
      
        cv2.imshow("Prediction", im)

    picam2.stop()  
    cv2.destroyAllWindows() 

    if detected_classes:
        global max_delay
        max_delay = 0
        print(f"Detected classes: {detected_classes}")
        for cls in detected_classes:
            if cls in class_delays:
                max_delay = max(max_delay, class_delays[cls])

    detected_classes.clear()
    return max_delay

# Function Start sterilization
def start_sterilization():
    global time, countdown_running, countdown_task
    start_button.pack_forget()  # hide start button when start sterilization
    GPIO.output(lamp_normal, False)  # lamp normal OFF
    update_status("lamp normal off")
    sleep(3)
    
    stop_button.pack(pady=20)
    GPIO.output(lamp_UVC, True)  # lamp UVC ON
    update_status("Sterilization in progress...")

    countdown_running = True
    update_countdown(time)  

# Stop sterilization
def stop_sterilization():
    global countdown_running
    GPIO.output(lamp_UVC, False)  # lamp UVC OFF
    stop_button.pack_forget()  # hide stop button when stop sterilization
    update_status("Sterilization complete. Open the door to remove items.")
    open_button.pack(pady=20)

    countdown_running = False  # stop time
    if countdown_task:
         root.after_cancel(countdown_task)  # Cancel the countdown task

# Countdown timer
def update_countdown(seconds):
    def countdown(i):
        global countdown_task
        if i >= 0 and countdown_running:  # Check if countdown is still running
            minutes, secs = divmod(i, 60)
            time_format = f"{minutes:02}:{secs:02}"
            countdown_label.configure(text=time_format)
            countdown_task = root.after(1000, countdown, i - 1)  # Call countdown again in 1 second
        else:
            countdown_label.configure(text="00:00")
            GPIO.output(lamp_UVC, False)  # Turn off UVC lamp when countdown finishes
            update_status("Sterilization complete. Open the door to remove items.")
            stop_button.pack_forget()
            open_button.pack(pady=20) 
    countdown(seconds)

# Initialize
if GPIO.input(door_sensor) == 0:  # Door is closed
    open_button.pack(pady=20) 
    update_status("Press 'Open Door' to insert items.")
else:  # Door is open
    update_status("Close the door to start sterilization.") 
    check_door_status()

# Run GUI in a separate thread to avoid blocking
def run_gui():
    root.mainloop()

# Start GUI in a separate thread
gui_thread = threading.Thread(target=run_gui)
gui_thread.daemon = True
gui_thread.start()
##