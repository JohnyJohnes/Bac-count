#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Raw capture of Full sensor area video stream in YUV format.
Display intensity plane.

3280x2464 native does not produce a picture, while 1640x1232 binned does?
"""

# import the necessary packages
from picamera.array import PiRGBArray, PiYUVArray
from picamera import PiCamera
import numpy as np
import time
import cv2

width = 1640 # 3280
height = 1232 # 2464
framerate = 5

# initialize the camera and grab a reference to the raw camera capture
camera = PiCamera()
camera.resolution = (width, height)
camera.framerate = framerate
rawCapture = PiYUVArray(camera, size=(width, height))
 
# allow the camera to warmup
time.sleep(0.1)

#cv2.namedWindow("Frame", cv2.WINDOW_NORMAL) # Create window with freedom of dimensions

# capture frames from the camera
for frame in camera.capture_continuous(rawCapture, format="yuv", use_video_port=True):
	# grab the raw NumPy array representing the image, then initialize the timestamp
	# and occupied/unoccupied text
	image = frame.array[:,:,0] # select only intensity channel
	print('Captured %dx%d image' % (image.shape[1], image.shape[0]))
	# show the frame
	cv2.imshow("Frame", image)
	key = cv2.waitKey(1) & 0xFF
 
	# clear the stream in preparation for the next frame
	rawCapture.truncate(0)
 
	# if the `q` key was pressed, break from the loop
	if key == ord("q"):
		break
