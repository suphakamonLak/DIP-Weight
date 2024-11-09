from IPython import display
import ultralytics
from ultralytics import YOLO
import cv2

# model = YOLO("best.pt")
cap = cv2.VideoCapture('./video/general-item-1.mp4')

desired_fps = 25
frame_delay = int(1000 / desired_fps)

if not cap.isOpened():
    print("Error: file not open")
    exit()

width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fourcc = cv2.VideoWriter_fourcc(*'mp4v')  
out = cv2.VideoWriter('output_video.mp4', fourcc, desired_fps, (width, height))

img_counter = 0  

while True:
    success, frame = cap.read()

    if success:
        results = model(frame)
        annotated_frame = results[0].plot()
        out.write(annotated_frame)

        cv2.imshow("General model", annotated_frame)

        k = cv2.waitKey(frame_delay) 
        if k & 0xFF == ord("q"): 
            break
        elif k % 256 == 32:  # spacebar trigger
            img_name = "frame_save{}.png".format(img_counter)
            cv2.imwrite(img_name, annotated_frame)
            img_counter += 1
            print("{} written!".format(img_name))
            frame = cv2.putText(
                frame,
                "img :{} save!".format(img_name),
                org=(50, 50),
                fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                fontScale=1,
                color=(255, 0, 0),
                thickness=2,
                lineType=cv2.LINE_AA
            )
    else:
        break

cap.release()
out.release()
cv2.destroyAllWindows()