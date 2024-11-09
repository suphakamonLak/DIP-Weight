from IPython import display
import ultralytics
from ultralytics import YOLO
import cv2

model = YOLO('./runs/segment/train8/weights/best.pt')

cap = cv2.VideoCapture(0)
desired_fps = 25
frame_delay = int(1000 / desired_fps)
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fourcc = cv2.VideoWriter_fourcc(*'mp4v') 
out = cv2.VideoWriter('realtime_video.mp4', fourcc, desired_fps, (width, height))

img_counter = 0

while cap.isOpened():
    ret, frame = cap.read()
    
    if not ret:
        break
    
    # predict
    results = model(frame)
    
    if results:
        for box in results[0].boxes:
            x, y, w, h = box.xywh[0]
            x, y, w, h = int(x), int(y), int(w), int(h)
            class_id = int(box.cls[0]) 
            class_name = model.names[class_id]  

            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
            cv2.putText(frame, class_name, (x, y - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    else:
        print("ไม่พบ bounding boxes ใน results")
    
    out.write(frame)
    cv2.imshow('Webcam Player', frame)
    
    k = cv2.waitKey(frame_delay)
    if k & 0xff == ord('q'):
        break
    elif k == 32:  # spacebar trigger
        img_name = "frame_save{}.png".format(img_counter)
        cv2.imwrite(img_name, frame)
        img_counter += 1
        print("{} written!".format(img_name))
        frame = cv2.putText(frame,
                            "img :{} save!".format(img_name),
                            org=(50, 50),
                            fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                            fontScale=1,
                            color=(255, 0, 0),
                            thickness=2,
                            lineType=cv2.LINE_AA
        )
    
cap.release()
out.release()
cv2.destroyAllWindows()