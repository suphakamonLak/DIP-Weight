import RPi.GPIO as GPIO
from time import sleep
import customtkinter as ctk
import cv2

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

# Sterilization times for objects
sterilization_times = {
    "sandals": 120,  # 2 minutes
    "coin": 60,    # 1 minute
    "mask": 90, # 1.5 minutes
    "box": 180,  # 3 minutes
}

detected_objects = set()
picam2 = Picamera2()

# GUI setup
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")
root = ctk.CTk()
root.geometry("750x450")
root.title("UVC Sterilization Cabinet")

# Status message
statusMessage = ctk.CTkLabel(root, text="Initializing...", font=("Arial", 16))
statusMessage.pack(pady=20)

state = "waiting"

# Global variable
sterilization_time = 0

# function
def start(): #ปุ่มเริ่มฆ่าเชื้อ
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

def cancel(): 
    startButton.pack_forget()  # Hide start button
    cancelButton.pack_forget()  # Hide cancel button 
    GPIO.output(lamp_UVC, False)
    GPIO.output(lamp_normal, True)  # Turn on normal lamp
    statusMessage.configure(text="Process canceled. Please open the door to reset.")
    root.update()
    openButton.pack(pady=10)  # Show open button again 
    state = "waiting"

def open(): 
    # Open door by unlocking it
    GPIO.output(door_lock, True)  # Unlock the door
    statusMessage.configure(text="Door unlocked. Please insert items.")
    root.update()
    sleep(0.5)
    GPIO.output(door_lock, False)  # Lock the door again
    openButton.pack_forget()  # Hide open button
    state = "waiting"

# Buttons 
openButton = ctk.CTkButton(root, text="Open", fg_color="blue", command=open)
startButton = ctk.CTkButton(root, text="Start", fg_color="green", command=start)
cancelButton = ctk.CTkButton(root, text="Cancel", fg_color="red", command=cancel)

openButton.pack(pady=10) 

# Main Loop
while True:
    # Check door close 
    if state == "waiting":
        if GPIO.input(door_sensor) == GPIO.LOW:
            statusMessage.configure(text="Door is closed. Please open it to insert items.")
            root.update()
            sleep(1)

        else: 
            GPIO.output(lamp_normal, True)
            GPIO.output(door_lock, True)  # Unlock the door
            statusMessage.configure(text="Door unlocked. Please insert items.")
            root.update()
            sleep(0.5)
            GPIO.output(door_lock, False)  # Lock door again
            state = "open"
            openButton.pack_forget()  # Hide open button ซ่อนปุ่ม open

    # Check door closed again after inserting items
    elif state == "open":
        while GPIO.input(door_sensor) == GPIO.HIGH:  # Wait until door is closed
            statusMessage.configure(text="Close the door to detect...")
            root.update()
            sleep(0.1)
        statusMessage.configure(text="Door is closed. Detecting items...")
        root.update()
        sleep(1)
        state = "insert"

    elif state == "insert":
        # Simulate object detection 
        statusMessage.configure(text="Door is closed. Detecting items...")
        root.update()
        sleep(1)
        # Simulate object detection 
        picam2 = Picamera2() # create obj picam2
        picam2.preview_configuration.main.size = (840,440) # size image
        picam2.preview_configuration.main.format = "RGB888" # setting image type RGB888
        picam2.preview_configuration.align() # position image and camera
        picam2.configure("preview")
        picam2.start()

        model = YOLO('/home/pi/Downloads/best_ncnn_model', task="segment") # load model for type segmentation
        my_file = open("/home/pi/YOLO/coco.txt", "r") # name class
        data = my_file.read()
        class_list = data.split("\n") # storage data each line
        count = 0
        detected_objects = set()
        
        while True: # loop read img from camera and read every 50 frames
            im = picam2.capture_array()
            
            count += 1
            if count % 50 != 0:
                continue
            
            im = cv2.flip(im,-1) # Flip the image so that the resulting image is in the correct position
            results = model.predict(im) # predict
            a = results[0].boxes.data # Retrieve the detected frame data
            px = pd.DataFrame(a).astype("float") # convert data a to pandas and make the data float type 
            
            for index,row in px.iterrows(): # loop data of the detected frames
                
                x1 = int(row[0])
                y1 = int(row[1])
                x2 = int(row[2])
                y2 = int(row[3])
                
                d = int(row[5]) # index class
                c = class_list[d] # class name
                confidence = float(row[4]) 
                
                if confidence >= 0.5:
                    cv2.rectangle(im,(x1,y1),(x2,y2),(0,0,255),2)
                    cvzone.putTextRect(im,f'{c} ({confidence: .2f})',(x1,y1),1,1)
                    detected_objects.update(c)
                
            cv2.imshow("Camera", im) # display

            if cv2.waitKey(1)==ord('q'):
                break
        cv2.destroyAllWindows()
        
        if detected_objects: 
            statusMessage.configure(text=f"Objects detected: {', '.join(detected_objects)}")
            root.update()
            # Calculate sterilization time 
            sterilization_time = max([sterilization_times[obj] for obj in detected_objects]) 
            statusMessage.configure(text=f"Sterilization time: {sterilization_time} seconds.")
            root.update()

            # Show Start and Cancel buttons
            startButton.pack(pady=10)
            cancelButton.pack(pady=10)
        else:
            statusMessage.configure(text="No items detected. Please open the door to reset.")
            root.update()
            current_state = "waiting"
    root.update()

# Clean up GPIO on exit
GPIO.cleanup()