import RPi.GPIO as GPIO
import time

lamp_UVC = 17  
fan = 24 

GPIO.setmode(GPIO.BCM)
GPIO.setup(lamp_UVC, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(fan, GPIO.OUT, initial=GPIO.LOW)
GPIO.setwarnings(False)

GPIO.output(lamp_UVC, True)
time.sleep(10)
GRIO.output(lamp_UVC, False)

GPIO.output(fan, True)
time.sleep(10)
GPIO.output(fan, True)