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
import numpy as np
from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QWidget, QDesktopWidget, QTextEdit, QApplication, QDoubleSpinBox, QSpinBox, QGridLayout, QHBoxLayout, QVBoxLayout, QLabel, QSpacerItem, QSizePolicy
from PyQt5.QtGui import QCloseEvent, QPixmap, QImage
from picamera.array import PiRGBArray
from picamera import PiCamera

WIDTH = 3280
HEIGHT = 2464
FRAME_RATE = 10

class PiVideoStream(QThread):    
    sigMsg = pyqtSignal(str)  # Message signal
    ready = pyqtSignal(np.ndarray)
    
    def __init__(self, resolution=(320, 240), framerate=24):
        super().__init__()
        self.name = "PiVideoStream"
        self.sigMsg.emit("Init " + self.name)
        self.camera = PiCamera()
        self.camera.resolution = resolution
        self.camera.framerate = framerate
        self.rawCapture = PiRGBArray(self.camera, size=resolution)
        self.stream = self.camera.capture_continuous(self.rawCapture, format="bgr", use_video_port=True)
        self.frame = None

    def run(self):
        try:
            for f in self.stream:
                self.frame = f.array  # grab the frame from the stream 
                self.rawCapture.truncate(0)  # clear the stream in preparation for the next frame
                self.ready.emit(self.frame)
                self.sigMsg.emit(self.name + ": Frame captured.")
        except Exception as err:
            self.sigMsg.emit(self.name + ": Error running thread.")
            
    def read(self):
        # return the frame most recently read
        return self.frame

    @pyqtSlot()
    def stop(self):
##        self.stream.close()
        self.rawCapture.close()
##        self.camera.close()
        self.quit()
        self.sigMsg.emit(self.name + ": closed.")
        
        
class MainWindow(QWidget):
    closing = pyqtSignal()  # Window closed signal 
    sigMsg = pyqtSignal(str)  # Message signal

    def __init__(self):
       super().__init__()
       self.name = "MainWindow"
       self.sigMsg.emit("Init " + self.name)       
       self.image = None
       self.initUI()

    def initUI(self):
        self.setWindowTitle('PyQT GUI with OpenCV and Picamera acquisition thread')
        self.move(100,100)
        # Labels
        self.PixImage = QLabel()
        # Spinboxes     
        self.frameRateSpinBox = QSpinBox(self)
        self.frameRateSpinBoxTitle = QLabel("Sample time")
        self.frameRateSpinBox.setSuffix(" [ms]")
        self.frameRateSpinBox.setMinimum(1)
        self.frameRateSpinBox.setMaximum(999)
        self.frameRateSpinBox.setValue(FRAME_RATE)         
        # Compose layout grid
        keyWidgets = [self.frameRateSpinBoxTitle]
        valueWidgets = [self.frameRateSpinBox]
        widgetLayout = QGridLayout()
        for index, widget in enumerate(keyWidgets):
            if widget is not None:
                widgetLayout.addWidget(widget, index, 0, Qt.AlignLeft)
        for index, widget in enumerate(valueWidgets):
            if widget is not None:
                widgetLayout.addWidget(widget, index, 1, Qt.AlignLeft)
        widgetLayout.setSpacing(10)
        widgetLayout.addItem(QSpacerItem(0, 0, QSizePolicy.Minimum,QSizePolicy.Expanding))  # variable space
        layout = QHBoxLayout()
        layout.addLayout(widgetLayout, Qt.AlignTop|Qt.AlignCenter)
        layout.addWidget(self.PixImage, Qt.AlignTop|Qt.AlignCenter)
        layout.setSpacing(10)
        self.setLayout(layout)

    @pyqtSlot(np.ndarray)
    def update(self, img=None):
        if not(img is None):  # we have a new image
            self.image = img
            height, width = self.image.shape[:2]  # Get dimensions
            qImage = QImage(self.image.data, width, height, width * 3, QImage.Format_RGB888)  # Convert from OpenCV to PixMap   
            self.PixImage.setPixmap(QPixmap(qImage))
            self.PixImage.show()        
        
    def closeEvent(self, event: QCloseEvent):
        self.closing.emit()
        event.accept()        
        

class LogWindow(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Log")
        self.move(100,100)
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
    time.sleep(2.0)
    
    # Connect signals and slots

    # loop over some frames...this time using the threaded stream
##    while fps._numFrames < args["num_frames"]:
##            # grab the frame from the threaded video stream and resize it
##            # to have a maximum width of 400 pixels
##            frame = vs.read()
####            frame = imutils.resize(frame, width=400)
##     
##            cv2.imshow("Frame", frame)
##            key = cv2.waitKey(1) & 0xFF
##     
## 
##    vs.stop()    
##    qTimer.timeout.connect(imgAcqThread.start)  # Start thread on QTimer timeout events
##    worker.imgReady.connect(mainWindow.onImgReady)  # Post worker's result to main Window
##    mainWindow.closing.connect(qTimer.stop)  # Stop timer
    vs.sigMsg.connect(logWindow.append)  # Log messages
    vs.ready.connect(mainWindow.update)  # Stream images to main window
    mainWindow.sigMsg.connect(logWindow.append)  # Log messages
    mainWindow.closing.connect(vs.stop)  # Stop video stream and quit thread
    mainWindow.closing.connect(logWindow.close)  # Close log window
    mainWindow.closing.connect(app.exit)  # Close app
##    mainWindow.frameRateSpinBox.valueChanged.connect(qTimer.setInterval)
##    mainWindow.segLengthSpinBox.valueChanged.connect(worker.setSegmentLength)
##    mainWindow.nrOfSegmentsSpinBox.valueChanged.connect(worker.setnrOfSegments)
##    mainWindow.noiseOffsetSpinBox.valueChanged.connect(worker.setNoiseOffset)
##    mainWindow.noiseGainSpinBox.valueChanged.connect(worker.setNoiseGain)    

    # Start the show
    logWindow.show()
    mainWindow.show()
    sys.exit(app.exec_())
            
