#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Capture grey scale image from luminance channel of YUV raw image
See: https://picamera.readthedocs.io/en/release-1.11/index.html
"""

import picamera
import numpy as np
import cv2
from time import sleep, time

width = 3280
height = 2464

# According to the tutorial, it is considerably more efficient to have the Pi's GPU perform the resizing when capturing an image
# is this also true for transparent API?
N = 4
# Simply taking a picture at a lower resolution seems to be faster and give similar results
# Nevertheless, the still port seems to be quite slow
# Videoport is much faster, but seems to lack a denoising filter.
# Wonder whether this filter has an effect on the processing results

# Calculate the actual image size in the stream (accounting for rounding of the resolution)
fwidth = (width//N + 31) // 32 * 32
fheight = (height//N + 15) // 16 * 16
Y_data = np.empty((fheight, fwidth), dtype=np.uint8) # buffer just large enough for Y plane

with picamera.PiCamera() as camera:
        camera.resolution = (width,height)
#        camera.image_effect = 'sketch' # Apply effects that seem well suited for line detection
        sleep(1)
        start = time()
        try:
                if N>1:
                        camera.capture(Y_data,format='yuv', resize=(width//N,height//N), use_video_port=True)
                else:
                        camera.capture(Y_data,format='yuv', use_video_port=False)
        except IOError:
                pass
        finally:
                print("Capturing time: ", time() - start)
                camera.close()
# picamera will deliberately write as much as it can to the buffer before raising an exception to support this use-case 

cv2.imshow("Image", Y_data)
cv2.waitKey(0)

start = time()
Y_data = cv2.bilateralFilter(Y_data,11,22,11)
print("Bilateral filtering time: ", time() - start)

#start = time()
#Y_data = cv2.reduce(Y_data, 0, cv2.REDUCE_AVG, dtype=cv2.CV_32S)
#print("Reducing time: ", time() - start)

start = time()
Y_data = Y_data[:height//N, :width//N]
cv2.imwrite("image.png", Y_data)
print("Disc writing time: ", time() - start)

