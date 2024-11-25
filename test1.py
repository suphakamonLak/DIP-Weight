import RPi.GPIO as GPIO
from time import sleep
import customtkinter as ctk

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
start_button = ctk.CTkButton(root, text="Start", fg_color="green", command=lambda: toggle_door())
stop_button = ctk.CTkButton(root, text="Stop", fg_color="red", command=lambda: stop_sterilization())

# Function update status
def update_status(message):
    status_label.configure(text=message)
    root.update()

# Function Open door
def open_door():
    GPIO.output(door_lock, False)  # Unlock the door
    update_status("Door unlocked.")
    open_button.pack_forget() # Hide open button when door unlocked
    check_door_status()

# Function Toggle door (this will be linked to start_button)
def toggle_door():
    if GPIO.input(door_sensor) == 1:  # Door is open
        close_door()
    else:  # Door is closed
        open_door()

# Function Close door
def close_door():
    GPIO.output(door_lock, True)  # Lock the door
    update_status("Door locked.")
    start_button.configure(text="Open Door")  # Change button to "Open Door" when door is closed
    check_door_status()

# Function Check door status
def check_door_status():
    global time
    while GPIO.input(door_sensor) == 1:  # Door open
        update_status("Door is opened, please insert packet and close the door.")
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
    start_button.configure(text="Start Sterilization")  # Change text to Start Sterilization

# Function predict item
def predict_item():
    return(5)

# Function Start sterilization
def start_sterilization():
    global time, countdown_running, countdown_task
    start_button.pack_forget()  # Hide start button when start sterilization
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
    stop_button.pack_forget()  # Hide stop button when stop sterilization
    update_status("Sterilization complete. Open the door to remove items.")
    open_button.pack(pady=20)

    countdown_running = False  # Stop timer
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

root.mainloop()
