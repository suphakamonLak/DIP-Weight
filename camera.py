import cv2
from picamera2 import Picamera2 
import pandas as pd
from ultralytics import YOLO
import cvzone
import time

picam2 = Picamera2()
picam2.preview_configuration.main.size = (840, 440) 
picam2.preview_configuration.main.format = "RGB888"
picam2.preview_configuration.align()
picam2.configure("preview") 
picam2.start()

model = YOLO('/home/pi/YOLO/NCNN/adam-100-epochs/best_ncnn_model', task="segment")

with open("/home/pi/YOLO/coco.txt", "r") as my_file:
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

frame_count = 0
detected_classes = set()

while not detected_classes:
    frame_count += 1
    im = picam2.capture_array() 
    im = cv2.flip(im, -1)  

    if frame_count < 100:
        cv2.putText(
            im, 
            f"Frame: {frame_count}", 
            (50, 50), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            1, 
            (0, 255, 0), 
            2
        )
        cv2.imshow("Preview", im)
        print(f"Waiting... Frame {frame_count}")
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        continue

    results = model.predict(im, verbose=False) 
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

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

picam2.stop()
cv2.destroyAllWindows()

if detected_classes:
    max_delay = 0
    print(f"Detected classes: {detected_classes}")
    for cls in detected_classes:
        if cls in class_delays:
            max_delay = max(max_delay, class_delays[cls])

    print(f"Waiting for {max_delay} seconds...")
    time.sleep(max_delay)

detected_classes.clear()
print("Program finished.")