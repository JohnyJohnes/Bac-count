#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
PyQT GUI with OpenCV and Picamera acquisition thread
"""

import os
import glob
import sys
import cv2
import time
from datetime import datetime
import numpy as np
from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QWidget, QDesktopWidget, QTextEdit, QApplication, QDoubleSpinBox, QSpinBox, QGridLayout, QHBoxLayout, QVBoxLayout, QLabel, QSpacerItem, QSizePolicy, QPushButton
from PyQt5.QtGui import QCloseEvent, QPixmap, QImage
from picamera.array import PiRGBArray, PiYUVArray
from picamera import PiCamera

## See https://picamera.readthedocs.io/en/release-1.13/fov.html#camera-modes
WIDTH = 1640 # 3280 # 1920
HEIGHT = 1232 # 2464 # 1088
FRAME_RATE = 10
USE_VIDEO_PORT = False

## Bayer array is ook mogelijk
## https://picamera.readthedocs.io/en/release-1.10/api_array.html

class PiVideoStream(QThread):    
    sigMsg = pyqtSignal(str)  # Message signal
    ready = pyqtSignal(np.ndarray)
    
    def __init__(self, resolution=(640,480), framerate=24):
        super().__init__()
        self.name = "PiVideoStream"
        self.camera = PiCamera()
        self.initCamera(resolution, framerate)
        self.pause = False        

    def __del__(self):
        self.wait()

    def run(self):
        try:
            for f in self.stream:
                self.rawCapture.truncate(0)  # clear the stream in preparation for the next frame
                if (self.pause == True):
                    self.sigMsg.emit(self.name + ": paused.")
                    break  # return from thread is needed
                else:
                    self.frame = f.array  # grab the frame from the stream
                    self.ready.emit(self.frame)
##                    self.sigMsg.emit(self.name + ": frame captured.")
        except Exception as err:
            self.sigMsg.emit(self.name + ": error running thread.")
            pass
        finally:
            self.sigMsg.emit(self.name + ": quit.")

    def initCamera(self, resolution=(640,480), framerate=24, format="bgr", use_video_port=False):
        self.sigMsg.emit(self.name + "Init: resolution = " + str(resolution))
        self.camera.resolution = resolution
        self.camera.framerate = framerate
        self.rawCapture = PiRGBArray(self.camera, size=self.camera.resolution)
        self.stream = self.camera.capture_continuous(self.rawCapture, format, use_video_port)
        self.frame = None
        time.sleep(2)                

    @pyqtSlot()
    def stop(self):
        self.pause = True
        self.wait()
##        self.rawCapture.close()
##        self.camera.close()
        self.quit()
        self.sigMsg.emit(self.name + ": closed.")

    @pyqtSlot()
    def changeCameraSettings(self, resolution=(640,480), framerate=24, format="bgr", use_video_port=False):
        self.pause = True
        self.wait()
        self.initCamera(resolution, framerate, format, use_video_port)
        self.pause = False
        self.start()  # restart thread
        
        
class MainWindow(QWidget):
    closing = pyqtSignal()  # Window closed signal 
    sigMsg = pyqtSignal(str)  # Message signal

    def __init__(self):
       super().__init__()
       self.name = "MainWindow"
       self.sigMsg.emit("Init " + self.name)       
       self.image = None
       self.prevClockTime = None
       self.imageScalingFactor = 1.0
       self.imageScalingStep = 0.1       
       self.initUI()

    def initUI(self):
        self.setWindowTitle('PyQT GUI with OpenCV and Picamera acquisition thread')
        self.move(300,100)
        screen = QDesktopWidget().availableGeometry()
        self.imageWidth = round(screen.height() * 0.8)
        self.imageHeight = round(screen.width() * 0.8)        
        # Labels
        self.PixImage = QLabel()
        self.procClockLabel = QLabel()        
        # Spinboxes     
        self.frameRateSpinBox = QSpinBox(self)
        self.frameRateSpinBoxTitle = QLabel("Sample time")
        self.frameRateSpinBox.setSuffix(" [ms]")
        self.frameRateSpinBox.setMinimum(1)
        self.frameRateSpinBox.setMaximum(999)
        self.frameRateSpinBox.setValue(FRAME_RATE)
        # Buttons
        self.button = QPushButton("Button1")
        # Compose layout grid
        keyWidgets = [self.frameRateSpinBoxTitle]
        valueWidgets = [self.frameRateSpinBox, self.button]
        widgetLayout = QGridLayout()
        for index, widget in enumerate(keyWidgets):
            if widget is not None:
                widgetLayout.addWidget(widget, index, 0, Qt.AlignLeft)
        for index, widget in enumerate(valueWidgets):
            if widget is not None:
                widgetLayout.addWidget(widget, index, 1, Qt.AlignLeft)
        widgetLayout.setSpacing(10)
        widgetLayout.addItem(QSpacerItem(0, 0, QSizePolicy.Minimum,QSizePolicy.Expanding))  # variable space
        widgetLayout.addWidget(self.procClockLabel,index+1,0,alignment=Qt.AlignLeft)
        layout = QHBoxLayout()
        layout.addLayout(widgetLayout, Qt.AlignTop|Qt.AlignCenter)
        layout.addWidget(self.PixImage, Qt.AlignTop|Qt.AlignCenter)
        layout.setSpacing(10)
        self.setLayout(layout)

    @pyqtSlot(np.ndarray)
    def update(self, image=None):
        if not(image is None):  # we have a new image
            self.image = image
            if self.imageScalingFactor > 0 and self.imageScalingFactor < 1:  # Crop the image to create a zooming effect
                height, width = image.shape[:2]  # get dimensions
                delta_height = round(height * (1 - self.imageScalingFactor) / 2)
                delta_width = round(width * (1 - self.imageScalingFactor) / 2)
                image = image[delta_height:height - delta_height, delta_width:width - delta_width]
            height, width = image.shape[:2]  # get dimensions
            if self.imageHeight != height or self.imageWidth != width:  # we need scaling
                scaling_factor = self.imageHeight / float(height)  # get scaling factor
                if self.imageWidth / float(width) < scaling_factor:
                    scaling_factor = self.imageWidth / float(width)
                    image = cv2.resize(image, None, fx=scaling_factor, fy=scaling_factor,
                                       interpolation=cv2.INTER_AREA)  # resize image
            height, width = image.shape[:2]  # get dimensions
            qImage = QImage(image.data, width, height, width * 3, QImage.Format_RGB888)  # Convert from OpenCV to PixMap
            self.PixImage.setPixmap(QPixmap(qImage))
            self.PixImage.show()
            
    @pyqtSlot(np.ndarray)
    def procClock(self, image=None):
        clockTime = datetime.now()
        if not(self.prevClockTime is None):
            timeDiff = clockTime - self.prevClockTime
            self.procClockLabel.setText("Processing time: " + "{:4d}".format(round(1000*timeDiff.total_seconds())) + " ms")
        self.prevClockTime = clockTime

        
    def closeEvent(self, event: QCloseEvent):
        self.closing.emit()
        event.accept()

    def wheelEvent(self, event):
        if (event.angleDelta().y() > 0) and (self.imageScalingFactor > self.imageScalingStep):  # zooming in
            self.imageScalingFactor -= self.imageScalingStep
        elif (event.angleDelta().y() < 0) and (self.imageScalingFactor < 1.0):  # zooming out
            self.imageScalingFactor += self.imageScalingStep        
        self.imageScalingFactor = round(self.imageScalingFactor, 2)  # strange behaviour, so rounding is necessary
        self.update()  # redraw the image with different scaling        
        

class LogWindow(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Log")
        self.move(0,100)
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.resize(400, 800)        
        self.log = QTextEdit()
        layout.addWidget(self.log)        

    @pyqtSlot(str)
    def append(self, s):
        self.log.append(s)
        

if __name__ == '__main__':
    app = QApplication(sys.argv)
    print("App started!")
    
    # Instantiate objects
    mainWindow = MainWindow()
    logWindow = LogWindow()
    vs = PiVideoStream((WIDTH, HEIGHT), FRAME_RATE)
    vs.start()
    
    # Connect signals and slots
    vs.sigMsg.connect(logWindow.append)  # Log messages
    vs.ready.connect(mainWindow.update)  # Stream images to main window
    vs.ready.connect(mainWindow.procClock)  # Measure time delay
    mainWindow.sigMsg.connect(logWindow.append)  # Log messages
    mainWindow.button.clicked.connect(lambda: vs.changeCameraSettings(resolution=(640,480), use_video_port=True))  # Change resolution
    mainWindow.closing.connect(logWindow.close)  # Close log window
##    mainWindow.closing.connect(vs.stop)  # Stop video stream and quit thread
##    mainWindow.closing.connect(app.exit)  # Close app

    
##    mainWindow.frameRateSpinBox.valueChanged.connect(qTimer.setInterval)
##    mainWindow.segLengthSpinBox.valueChanged.connect(worker.setSegmentLength)
##    mainWindow.nrOfSegmentsSpinBox.valueChanged.connect(worker.setnrOfSegments)
##    mainWindow.noiseOffsetSpinBox.valueChanged.connect(worker.setNoiseOffset)
##    mainWindow.noiseGainSpinBox.valueChanged.connect(worker.setNoiseGain)    

    # Start the show
    logWindow.show()
    mainWindow.show()
    sys.exit(app.exec_())
            
