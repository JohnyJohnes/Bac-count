#!/usr/bin/python3
# -*- coding: utf-8 -*-
import cv2 as cv
import numpy as np
from matplotlib import pyplot as plt

#Read image
img = cv.imread("/home/pi/Desktop/blobedited.png", 0)
#Blur image to remove noise
img = cv.medianBlur(img,5)

#Create a binary image
ret,thresh1 = cv.threshold(img,105,255,cv.THRESH_BINARY)



# Set up the detector parameters
params = cv.SimpleBlobDetector_Params()
#Filter parameters
params.filterByArea = False
params.filterByCircularity = True
params.filterByCircularity = False
params.filterByConvexity = False
params.filterByInertia = False
#MinMax parameters
params.minCircularity = 0.0
params.minConvexity = 0.0
params.maxInertiaRatio = 0.001
params.minThreshold = 10
params.maxThreshold = 200
params.minArea = 0
params.minDistBetweenBlobs = 1
#Color of blobs, black in this case
params.blobColor = 0

#Create detector with these parameters
detector = cv.SimpleBlobDetector_create(params)

#Floodfill to remove border(border cells can't be counted anyways)
h, w = thresh1.shape[:2]
mask = np.zeros((h+2, w+2), np.uint8)
cv.floodFill(thresh1, mask, (0,0), 255)
cv.floodFill(thresh1, mask, (0,0), 0)
# Detect blobs and print amount of blobs
keypoints = detector.detect(thresh1)

 
# Draw detected blobs as red circles.
#cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS ensures the size of the circle corresponds to the size of blob
im_with_keypoints = cv.drawKeypoints(thresh1, keypoints, np.array([]), (0,0,255), cv.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)
 
# Show keypoints, make window 600x600 because the original resolution is way too large.
cv.namedWindow('blob', cv.WINDOW_NORMAL)
cv.resizeWindow('blob', 600,600)
cv.imshow('blob', im_with_keypoints)
cv.waitKey(0)
