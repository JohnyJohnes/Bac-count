#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
PyQT GUI with Picamera acquisition thread and OpenCV processing thread
"""
import os
import glob
import sys
import cv2
import time
from datetime import datetime
import numpy as np
from PyQt5.QtCore import Qt, QObject, QThread, QTimer, pyqtSignal, pyqtSlot, QSettings
from PyQt5.QtWidgets import QWidget, QDesktopWidget, QApplication, QGridLayout, QHBoxLayout, QVBoxLayout
from PyQt5.QtWidgets import QLabel, QSpacerItem, QSizePolicy, QPushButton, QComboBox, QCheckBox, QTextEdit, QDoubleSpinBox, QSpinBox
from PyQt5.QtGui import QCloseEvent, QPixmap, QImage
from picamera.array import PiRGBArray, PiYUVArray
from picamera import PiCamera
from threading import Thread

## See https://picamera.readthedocs.io/en/release-1.13/fov.html#camera-modes
WIDTH = 1640 # 3280 # 1920
HEIGHT = 1232 # 2464 # 1088
FRAME_RATE = 10
USE_VIDEO_PORT = False

## Bayer array is ook mogelijk
## https://picamera.readthedocs.io/en/release-1.10/api_array.html

class ImageProcessing(QThread):
    """
    ksize - Median Blur aperture linear size; it must be odd and greater than 1, for example: 3, 5, 7 ...
    adaptiveThresholdBlocksize -
    adaptiveThresholdOffset -
    showStep - Which image processing step to send via Py signal
    annotate -
    """
    name = "ImageProcessing"
    image = None
    pause = False
    invertBinary = True
    ksize = 3
    blocksize = 3
    offset = 2
    showProcStep = 0
    annotateImage = False    
    sigMsg = pyqtSignal(str)  # Message signal
    ready = pyqtSignal(np.ndarray)
   
    def __init__(self):
        super().__init__()

    @pyqtSlot(np.ndarray)
    # Note that we need this wrapper around the Thread run function, since the latter will not accept any parameters
    def go(self, image=None): 
        try:
            if self.isRunning():  # thread is already running
                self.sigMsg.emit(self.name + ": busy, frame dropped.")
            elif not(image is None):  # we have a new image
                self.image = image
                self.start()
        except Exception as err:
            self.sigMsg.emit(self.name + ": exception " + str(err))
            pass

    def run(self):
        if not(self.image is None):  # we have a new image
            self.sigMsg.emit(self.name + ": started.")
            # Preprocess the image
            # rotImage = rotateImage(self.image, self.rotAngle)
            # if self.cropXp2 > 0 and self.cropYp2 > 0:  # use the same crop as before
            #     cropImage = rotImage[self.cropYp1:self.cropYp2, self.cropXp1:self.cropXp2]
            # else:
            #     cropImage = rotImage[self.cropYp1:(rotImage.shape)[
            #         0], self.cropXp1:(rotImage.shape)[1]]
            grayImage = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
            blurredImage = cv2.medianBlur(grayImage, self.ksize)
            BWImage = cv2.adaptiveThreshold(
                blurredImage, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, self.invertBinary, self.blocksize, self.offset)

            # Compose Image signal
            if self.showProcStep == 0:
                img = self.image
                # img = cv2.cvtColor(cropImage, cv2.COLOR_BGR2RGB)
            elif self.showProcStep == 1:
                img = cv2.cvtColor(grayImage, cv2.COLOR_GRAY2RGB)
            elif self.showProcStep == 2:
                img = cv2.cvtColor(blurredImage, cv2.COLOR_GRAY2RGB)
            elif self.showProcStep == 3:
                img = cv2.cvtColor(BWImage, cv2.COLOR_GRAY2RGB)
            else:
                img = None
            # if self.annotateImage:  # Annotate the image
                # img[:, ~row_mask] = 0
                # img[~col_mask, :] = 0
                # for row in blobData:  # Show RoIs
                #     tl = (row[0], row[1])
                #     br = (row[0] + row[2], row[1] + row[3])
                #     cv2.rectangle(img, tl, br, (255, 0, 0), 1)
            self.ready.emit(img)

    @pyqtSlot(int)
    def setProcStep(self, showStep):
        if showStep >= 0:
            self.wait()
            self.showProcStep = showStep

    @pyqtSlot(int)
    def setAnnotate(self, annotate):
        self.wait()
        self.annotateImage = True if annotate else False

    @pyqtSlot(int)
    def setInvertBinary(self, invert):
        self.wait()
        self.invertBinary = True if invert else False

    @pyqtSlot(int)
    def setAdaptiveThresholdOffset(self, offset):
        self.wait()
        self.offset = offset  # if self.invertBinary else -offset                

class PiVideoStream(QThread):
    name = "PiVideoStream"
    sigMsg = pyqtSignal(str)  # Message signal
    ready = pyqtSignal(np.ndarray)
    pause = False
    
    def __init__(self, resolution=(640,480), framerate=24):
        super().__init__()
        self.camera = PiCamera()
        self.initCamera(resolution, framerate)

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
            self.sigMsg.emit(self.name + ": exception " +str(err))
            pass
        # finally:
        #     self.sigMsg.emit(self.name + ": quit.")

    def initCamera(self, resolution=(640,480), framerate=24, format='bgr', effect='none', use_video_port=False):
        self.sigMsg.emit(self.name + "Init: resolution = " + str(resolution))
        self.camera.resolution = resolution
        self.camera.image_effect = effect
        # dunno if setting awb mode manually is really useful
        self.camera.awb_mode = 'off'
        self.camera.awb_gains = 5.0
        self.camera.meter_mode = 'average'
        self.camera.exposure_mode = 'auto'  # 'sports' to reduce motion blur, 'off'after init to freeze settings
        self.camera.framerate = framerate
        self.rawCapture = PiRGBArray(self.camera, size=self.camera.resolution)
        self.stream = self.camera.capture_continuous(self.rawCapture, format, use_video_port)
        self.frame = None
        time.sleep(2)                

    @pyqtSlot()
    def stop(self):
        self.pause = True
        self.wait()
        # proper closing gives a segmentation fault?
        # self.rawCapture.close()
        # self.camera.close()
        self.quit()
        self.sigMsg.emit(self.name + ": closed.")

    @pyqtSlot()
    def changeCameraSettings(self, resolution=(640,480), framerate=24, format="bgr", effect='none', use_video_port=False):
        self.pause = True
        self.wait()
        self.initCamera(resolution, framerate, format, effect, use_video_port)
        self.pause = False
        self.start()  # restart thread
        
        
class MainWindow(QWidget):
    name = "MainWindow"
    closing = pyqtSignal()  # Window closed signal 
    sigMsg = pyqtSignal(str)  # Message signal

    def __init__(self):
       super().__init__()
       self.cwd = os.getcwd()
       self.settings = QSettings(self.cwd + "/" + os.path.basename(__file__) + "settings.ini", QSettings.IniFormat)
       self.image = None
       self.prevClockTime = None
       self.imageScalingFactor = 1.0
       self.imageScalingStep = 0.1       
       self.initUI()
       self.loadSettings()       

    def initUI(self):
        self.setWindowTitle('PyQT GUI with OpenCV and Picamera acquisition thread')
        self.move(300,100)
        screen = QDesktopWidget().availableGeometry()
        self.imageWidth = round(screen.height() * 0.8)
        self.imageHeight = round(screen.width() * 0.8)        
        # Labels
        self.PixImage = QLabel()
        self.procClockLabel = QLabel()
        # Combos
        self.showProcStepCombo = QComboBox(self)
        self.showProcStepCombo.addItem("Original")
        self.showProcStepCombo.addItem("Gray")
        self.showProcStepCombo.addItem("Filtered")
        self.showProcStepCombo.addItem("BW")
        # Checkboxes
        self.showAnnotated = QCheckBox("Annot")
        self.invertBinary = QCheckBox("Invert")
        # Spinboxes     
        self.frameRateSpinBox = QSpinBox(self)
        self.frameRateSpinBoxTitle = QLabel("Sample time")
        self.frameRateSpinBox.setSuffix(" [ms]")
        self.frameRateSpinBox.setMinimum(1)
        self.frameRateSpinBox.setMaximum(999)
        self.frameRateSpinBox.setValue(FRAME_RATE)
        self.offsetSpinBoxTitle = QLabel("offset")
        self.offsetSpinBox = QSpinBox(self)
        self.offsetSpinBox.setMinimum(-10)
        self.offsetSpinBox.setMaximum(10)
        # Buttons
        self.button = QPushButton("Button1")
        # Compose layout grid
        self.keyWidgets = [self.showProcStepCombo, self.showAnnotated, self.invertBinary, self.offsetSpinBoxTitle, self.frameRateSpinBoxTitle]
        self.valueWidgets = [None, None, None, self.offsetSpinBox, self.frameRateSpinBox, self.button]
        widgetLayout = QGridLayout()
        for index, widget in enumerate(self.keyWidgets):
            if widget is not None:
                widgetLayout.addWidget(widget, index, 0, Qt.AlignLeft)
        for index, widget in enumerate(self.valueWidgets):
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
        try:
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
        except Exception as err:
            self.sigMsg.emit(self.name + ": exception " + str(err))
            pass
        # finally:
        #     self.sigMsg.emit(self.name + ": quit.")

    @pyqtSlot(np.ndarray)
    def procClock(self, image=None):
        clockTime = datetime.now()
        if not(self.prevClockTime is None):
            timeDiff = clockTime - self.prevClockTime
            self.procClockLabel.setText("Processing time: " + "{:4d}".format(round(1000*timeDiff.total_seconds())) + " ms")
        self.prevClockTime = clockTime
        
    def closeEvent(self, event: QCloseEvent):
        self.saveSettings()
        self.closing.emit()
        event.accept()

    def wheelEvent(self, event):
        if (event.angleDelta().y() > 0) and (self.imageScalingFactor > self.imageScalingStep):  # zooming in
            self.imageScalingFactor -= self.imageScalingStep
        elif (event.angleDelta().y() < 0) and (self.imageScalingFactor < 1.0):  # zooming out
            self.imageScalingFactor += self.imageScalingStep        
        self.imageScalingFactor = round(self.imageScalingFactor, 2)  # strange behaviour, so rounding is necessary
        self.update()  # redraw the image with different scaling        

    def loadSettings(self):
        for index, widget in enumerate(self.keyWidgets):  # retreive all labeled parameters
            if isinstance(widget, QLabel):
                if self.settings.contains(widget.text()):
                    self.valueWidgets[index].setValue(float(self.settings.value(widget.text())))
                    
    def saveSettings(self):
        print(self.name + ": saving settings to " + self.settings.fileName())        
        for index, widget in enumerate(self.keyWidgets):  # save all labeled parameters
            if isinstance(widget, QLabel):
                self.settings.setValue(widget.text(), self.valueWidgets[index].value())
        for index, widget in enumerate(self.valueWidgets):  # save all labeled parameters
            if isinstance(widget, QCheckBox):
                self.settings.setValue(widget.text(), widget.isChecked())
                
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
    logWindow = LogWindow()
    mainWindow = MainWindow()
    imgProc = ImageProcessing()
    vs = PiVideoStream((WIDTH, HEIGHT), FRAME_RATE)
    vs.start()
    
    # Connect signals and slots
    vs.sigMsg.connect(logWindow.append)  # Log messages
    vs.ready.connect(mainWindow.procClock)  # Measure time delay
    vs.ready.connect(imgProc.go, type=Qt.QueuedConnection)  # 
    mainWindow.sigMsg.connect(logWindow.append)  # Log messages
    mainWindow.showProcStepCombo.currentIndexChanged.connect(imgProc.setProcStep)
    mainWindow.invertBinary.stateChanged.connect(imgProc.setInvertBinary)
    mainWindow.offsetSpinBox.valueChanged.connect(imgProc.setAdaptiveThresholdOffset)
    mainWindow.button.clicked.connect(lambda: vs.changeCameraSettings(resolution=(640,480), effect='blur', use_video_port=True))  # Change resolution
    mainWindow.closing.connect(logWindow.close)  # Close log window
    imgProc.sigMsg.connect(logWindow.append)  # Log messages
    imgProc.ready.connect(mainWindow.update)  # Stream images to main window
    
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
    app.exec_()
