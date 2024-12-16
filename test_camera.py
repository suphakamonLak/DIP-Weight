import customtkinter as ctk
from picamera2 import Picamera2
import numpy as np
import PIL.Image, PIL.ImageTk

picam2 = Picamera2()
picam2.start()

def update_image():
    frame = picam2.capture_array()
    img = PIL.Image.fromarray(frame)
    img_tk = PIL.ImageTk.PhotoImage(image=img)
    image_label.configure(image=img_tk)
    image_label.image = img_tk  

    root.after(50, update_image)

# setting customtkinter window
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")
root = ctk.CTk()
root.geometry("750x450")
root.title("UVC Sterilization Cabinet")

# create Label
image_label = ctk.CTkLabel(root)
image_label.pack(padx=10, pady=10)


update_image()
root.mainloop()

# stop camera
picam2.stop()