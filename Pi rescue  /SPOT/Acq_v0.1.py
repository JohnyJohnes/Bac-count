#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
todo: temperature sensor, heater
"""

import os
import sys
import time
from datetime import datetime
import numpy as np
import cv2
from PyQt5.QtCore import Qt, QObject, QThread, QTimer, pyqtSignal, pyqtSlot, QSettings
from PyQt5.QtWidgets import QWidget, QDesktopWidget, QApplication, QGridLayout, QHBoxLayout, QVBoxLayout
from PyQt5.QtWidgets import QLabel, QSpacerItem, QSizePolicy, QPushButton, QComboBox, QCheckBox, QTextEdit, QDoubleSpinBox, QSpinBox
from PyQt5.QtGui import QCloseEvent, QPixmap, QImage
import pigpio
sys.path.append(r'../lib') # local libraries
from biorpi.pyqtpicam import PiVideoStream
from biorpi.log import LogWindow
from biorpi.dip import ImgEnhancer, ImgSegmenter, BlobDetector
from biorpi.af import AutoFocus
from biorpi.vc  import VoiceCoil
from biorpi.heater  import Heater

current_milli_time = lambda: int(round(time.time() * 1000))

## Camera parameters
## See https://picamera.readthedocs.io/en/release-1.13/fov.html#camera-modes
WIDTH = 1648 # 3280 # 1648  (1920 16:9)
HEIGHT = 1232 # 2464 # 1232 (1088 16:9)
FRAME_RATE = 10
USE_VIDEO_PORT = True

class MainWindow(QWidget):
    name = "MainWindow"
    closing = pyqtSignal()  # Window closed signal 
    message = pyqtSignal(str)  # Message signal
    image = None
    imageScalingFactor = 1.0
    imageScalingStep = 0.1        

    def __init__(self):
       super().__init__()
       self.prevClockTime = None
       self.settings = QSettings(os.path.splitext(os.path.basename(__file__))[0] + "_GUI_settings.ini", QSettings.IniFormat)
       self.initUI()
       self.loadSettings()       

    def initUI(self):
        self.appName = os.path.basename(__file__)
        self.setWindowTitle(self.appName)
        self.move(300,100)
        screen = QDesktopWidget().availableGeometry()
        self.imageWidth = round(screen.height() * 0.8)
        self.imageHeight = round(screen.width() * 0.8)        
        # Labels
        self.PixImage = QLabel()
        self.timerLabel = QLabel()
        self.imageQualityLabel = QLabel()
        # Buttons
        self.snapshotButton = QPushButton("Snapshot")
        self.snapshotButton.clicked.connect(self.snapshot)
        self.autoFocusButton = QPushButton("AutoFocus")
        # Spinboxes
        self.VCSpinBox = QDoubleSpinBox(self)
        self.VCSpinBoxTitle = QLabel("VC")
        self.VCSpinBox.setSingleStep(1)
        self.VCSpinBox.setSuffix("%")
        self.VCSpinBox.setMinimum(-100.0)
        self.VCSpinBox.setMaximum(100.0)
        self.VCSpinBox.setSingleStep(0.01)
        self.rotateSpinBox = QDoubleSpinBox(self)
        self.rotateSpinBoxTitle = QLabel("rotate")
        self.rotateSpinBox.setSuffix("°")
        self.rotateSpinBox.setMinimum(-5.0)
        self.rotateSpinBox.setMaximum(5.0)
        self.rotateSpinBox.setSingleStep(0.1)
        self.gammaSpinBox = QDoubleSpinBox(self)
        self.gammaSpinBoxTitle = QLabel("gamma")
        self.gammaSpinBox.setMinimum(0.0)
        self.gammaSpinBox.setMaximum(5.0)
        self.gammaSpinBox.setSingleStep(0.1)
        self.gammaSpinBox.setValue(1.0)
        self.claheSpinBox = QDoubleSpinBox(self)
        self.claheSpinBoxTitle = QLabel("clahe")
        self.claheSpinBox.setMinimum(0.0)
        self.claheSpinBox.setMaximum(10.0)
        self.claheSpinBox.setSingleStep(0.1)
        self.cropXp1Spinbox = QSpinBox(self)
        self.cropXp1SpinboxTitle = QLabel("xp1")
        self.cropXp1Spinbox.setMinimum(0)
        self.cropXp1Spinbox.setMaximum(WIDTH/2)
##        self.cropXp1Spinbox.setSingleStep(10)
        self.cropXp2Spinbox = QSpinBox(self)
        self.cropXp2SpinboxTitle = QLabel("xp2")
        self.cropXp2Spinbox.setMinimum(self.cropXp1Spinbox.value())
        self.cropXp2Spinbox.setMaximum(WIDTH)
##        self.cropXp2Spinbox.setSingleStep(10)
        self.cropXp2Spinbox.setValue(WIDTH)
##        self.cropXp2Spinbox.setSingleStep(10)
        self.cropYp1Spinbox = QSpinBox(self)
        self.cropYp1SpinboxTitle = QLabel("yp1")
        self.cropYp1Spinbox.setMinimum(0)
        self.cropYp1Spinbox.setMaximum(HEIGHT/2)
##        self.cropYp1Spinbox.setSingleStep(10)
        self.cropYp2Spinbox = QSpinBox(self)
        self.cropYp2SpinboxTitle = QLabel("yp2")
        self.cropYp2Spinbox.setMinimum(self.cropYp1Spinbox.value())
        self.cropYp2Spinbox.setMaximum(HEIGHT)
##        self.cropYp2Spinbox.setSingleStep(10)
        self.cropYp2Spinbox.setValue(HEIGHT)        
        # Compose layout grid
        self.keyWidgets = [self.VCSpinBoxTitle, self.rotateSpinBoxTitle, self.gammaSpinBoxTitle, self.claheSpinBoxTitle,
                           self.cropXp1SpinboxTitle, self.cropYp1SpinboxTitle, self.cropXp2SpinboxTitle, self.cropYp2SpinboxTitle]
        self.valueWidgets = [self.VCSpinBox, self.rotateSpinBox, self.gammaSpinBox, self.claheSpinBox,
                             self.cropXp1Spinbox, self.cropYp1Spinbox, self.cropXp2Spinbox, self.cropYp2Spinbox]
        widgetLayout = QGridLayout()
        for index, widget in enumerate(self.keyWidgets):
            if widget is not None:
                widgetLayout.addWidget(widget, index, 0, Qt.AlignCenter)
        for index, widget in enumerate(self.valueWidgets):
            if widget is not None:
                widgetLayout.addWidget(widget, index, 1, Qt.AlignCenter)
        widgetLayout.addItem(QSpacerItem(0, 0, QSizePolicy.Minimum,QSizePolicy.Expanding))  # variable space
        widgetLayout.addWidget(self.snapshotButton,index+1,0,alignment=Qt.AlignLeft)
        widgetLayout.addWidget(self.autoFocusButton,index+2,0,alignment=Qt.AlignLeft)
        widgetLayout.addWidget(self.imageQualityLabel,index+3,0,alignment=Qt.AlignLeft)
        widgetLayout.addWidget(self.timerLabel,index+4,0,alignment=Qt.AlignLeft)
        layout = QHBoxLayout()
        layout.addLayout(widgetLayout, Qt.AlignTop|Qt.AlignCenter)
        layout.addWidget(self.PixImage, Qt.AlignTop|Qt.AlignCenter)
##        layout.setSpacing(100)
        self.setLayout(layout)
##        self.showMaximized()

    @pyqtSlot(np.ndarray)
    def imgUpdate(self, image=None):
##        self.message.emit(self.name + ": height " + str(image.shape[0]))
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
            if len(image.shape) < 3:  # check nr of channels
                image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)  # convert to color image
            qImage = QImage(image.data, width, height, width * 3, QImage.Format_RGB888)  # Convert from OpenCV to PixMap
            self.PixImage.setPixmap(QPixmap(qImage))
            self.PixImage.show()

    @pyqtSlot()
    def kickTimer(self):
        clockTime = current_milli_time() # datetime.now()
        if self.prevClockTime is not None:
            timeDiff = clockTime - self.prevClockTime
            self.timerLabel.setText("Processing time: " + "{:4d}".format(round(timeDiff)) + " ms")
            self.message.emit(self.name + ": processing delay = " + str(round(timeDiff)) + " ms")            
##            self.timerLabel.setText("Processing time: " + "{:4d}".format(round(1000*timeDiff.total_seconds())) + " ms")
        self.prevClockTime = clockTime            

    def wheelEvent(self, event):
        if (event.angleDelta().y() > 0) and (self.imageScalingFactor > self.imageScalingStep):  # zooming in
            self.imageScalingFactor -= self.imageScalingStep
        elif (event.angleDelta().y() < 0) and (self.imageScalingFactor < 1.0):  # zooming out
            self.imageScalingFactor += self.imageScalingStep        
        self.imageScalingFactor = round(self.imageScalingFactor, 2)  # strange behaviour, so rounding is necessary
        self.imgUpdate()  # redraw the image with different scaling

    def closeEvent(self, event: QCloseEvent):
        self.saveSettings()
        self.closing.emit()
        event.accept()        

    def snapshot(self):
##        a mutex is needed here?
        if not(self.image is None):
            filename = self.appName + '_'+ str(current_milli_time()) + '.png'
            cv2.imwrite(filename, self.image)
            self.message.emit(self.name + ": image written to " + filename)

    def loadSettings(self):
        self.message.emit(self.name + ": Loading settings from " + self.settings.fileName())
        for index, widget in enumerate(self.keyWidgets):  # retreive all labeled parameters
            if isinstance(widget, QLabel):
                if self.settings.contains(widget.text()):
                    self.valueWidgets[index].setValue(float(self.settings.value(widget.text())))

    def saveSettings(self):
        self.message.emit(self.name + ": Saving settings to " + self.settings.fileName())
        for index, widget in enumerate(self.keyWidgets):  # save all labeled parameters
            if isinstance(widget, QLabel):
                self.settings.setValue(widget.text(), self.valueWidgets[index].value())
        for index, widget in enumerate(self.valueWidgets):  # save all labeled parameters
            if isinstance(widget, QCheckBox):
                self.settings.setValue(widget.text(), widget.isChecked())       


if __name__ == '__main__':
    app = QApplication(sys.argv)
    print("App started!")    
        
    # Instantiate objects
    logWindow = LogWindow()
    mainWindow = MainWindow()
    enhancer = ImgEnhancer()
    segmenter = ImgSegmenter(doPlot=False)
    detector = BlobDetector(doPlot=True)
    autoFocus = AutoFocus(doPlot=True)
    
    pio = pigpio.pi()
    vc = VoiceCoil(pio)
    heater = Heater(pio)
    vs = PiVideoStream(resolution=(WIDTH, HEIGHT), monochrome=True, framerate=FRAME_RATE, effect='blur', use_video_port=USE_VIDEO_PORT)
    vs.start()    
    
    # Connect GUI signals and slots
    mainWindow.rotateSpinBox.valueChanged.connect(enhancer.setRotateAngle)
    mainWindow.gammaSpinBox.valueChanged.connect(enhancer.setGamma)
    mainWindow.claheSpinBox.valueChanged.connect(enhancer.setClaheClipLimit)
    mainWindow.VCSpinBox.valueChanged.connect(vc.setVal)
    mainWindow.cropXp1Spinbox.valueChanged.connect(enhancer.setCropXp1)
    mainWindow.cropYp1Spinbox.valueChanged.connect(enhancer.setCropYp1)
    mainWindow.cropXp2Spinbox.valueChanged.connect(enhancer.setCropXp2)
    mainWindow.cropYp2Spinbox.valueChanged.connect(enhancer.setCropYp2)
        
    # Connect processing signals and slots
    vs.ready.connect(mainWindow.kickTimer)  # Measure time delay    
    vs.ready.connect(lambda: enhancer.imgUpdate(vs.frame), type=Qt.BlockingQueuedConnection)  # Connect video/image stream to processing Qt.BlockingQueuedConnection or QueuedConnection?
    enhancer.ready.connect(lambda: mainWindow.imgUpdate(enhancer.image), type=Qt.QueuedConnection) # Get enhanced image from object
##    enhancer.ready.connect(lambda: segmenter.start(enhancer.image), type=Qt.QueuedConnection) # Get enhanced image from object
##    segmenter.ready.connect(lambda: detector.start(segmenter.image, segmenter.ROIs), type=Qt.QueuedConnection)  # Stream RoIs to blobdetector
##    segmenter.ready.connect(lambda: mainWindow.imgUpdate(segmenter.image), type=Qt.QueuedConnection) # Stream images to main window
##    segmenter.ready.connect(lambda: mainWindow.imageQualityLabel.setText("Image quality: " + "{:.4f}".format(segmenter.imgQuality)))  # display image quality

    # Recipes invoked when autoFocusButton is pressed, and when autofocus is done
    mainWindow.autoFocusButton.pressed.connect(lambda: autoFocus.start(P_centre=vc.value, N_p=11, dP=1, N_n=5))  # start from current focus point
##    mainWindow.autoFocusButton.pressed.connect(lambda: vs.changeCameraSettings(resolution=(640,480), framerate=FRAME_RATE, format="bgr", effect='denoise', use_video_port=True))  # switch to fast mode
    segmenter.ready.connect(lambda: autoFocus.imgQualUpdate(segmenter.imgQuality)) # Stream image quality measure to autoFocus object
##    autoFocus.ready.connect(lambda: vs.changeCameraSettings(resolution=(WIDTH, HEIGHT), framerate=FRAME_RATE, effect='denoise', use_video_port=USE_VIDEO_PORT))  # switch to original mode
    autoFocus.value.connect(mainWindow.VCSpinBox.setValue)
    
    # Log messages    
    mainWindow.message.connect(logWindow.append)
    vs.message.connect(logWindow.append)
    enhancer.message.connect(logWindow.append)
    vc.message.connect(logWindow.append)
    segmenter.message.connect(logWindow.append)
    autoFocus.message.connect(logWindow.append)
    detector.message.connect(logWindow.append)
    
    # Recipes invoked when mainWindow is closed, note that scheduler stops other threads
    mainWindow.closing.connect(logWindow.close)  # Close log window
    mainWindow.closing.connect(vs.stop)  # Close videostream
    mainWindow.closing.connect(vc.stop)  # Kill voicecoil object (destructor doesn't work?
    mainWindow.closing.connect(heater.stop)  # Kill heater object
    mainWindow.closing.connect(autoFocus.stop)

    # Start the show
    logWindow.show()
    mainWindow.show()    
    app.exec_()
    pio.stop()
    
