from IPython import display
import ultralytics
from ultralytics import YOLO
import cv2
import matplotlib.pyplot as plt

model = YOLO('./runs/segment/train8/weights/best.pt')

# predict
img = cv2.imread("D:/Train project/General-Test/dataset/test/images/0a2b2630-sock_89.jpg")
result = model.predict(source=img, conf = 0.5) 
result[0].save(filename = 'result.jpg')# save image
img2 = cv2.imread('result.jpg')# read file

frame = cv2.hconcat([img,img2])
cv2.imwrite('img.jpg', frame)# save img comparison

frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
plt.imshow(frame)