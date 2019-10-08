#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
PyQT GUI for manual control of WormPlateScanner EPS_v1 (28BYJ motors)
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
import RPi.GPIO as GPIO
from picamera import PiCamera
from picamera.array import PiRGBArray, PiYUVArray
from RpiMotorLib import RpiMotorLib
    
## define GPIO pins, see https://github.com/gavinlyonsrepo/RpiMotorLib
X_motor_pins =  [6,13,19,26]
Y_motor_pins =  [5,22,27,17]
Z_motor_pins = [21,20,16,12]
X_limit_pin = 23
Y_limit_pin = 24
Z_limit_pin = 25

## See https://picamera.readthedocs.io/en/release-1.13/fov.html#camera-modes
WIDTH = 1640# 3280 # 1920 1640 
HEIGHT = 1232 # 2464 # 1088 1232
FRAME_RATE = 10
USE_VIDEO_PORT = False

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

class MainWindow(QWidget):
    name = "MainWindow"
    closing = pyqtSignal()  # Window closed signal 
    sigMsg = pyqtSignal(str)  # Message signal
    image = None
    imageScalingFactor = 1.0
    imageScalingStep = 0.1        

    def __init__(self):
       super().__init__()
##       self.cwd = os.getcwd()
##       self.settings = QSettings(self.cwd + "/" + os.path.basename(__file__) + "settings.ini", QSettings.IniFormat)
       self.initUI()

    def initUI(self):
        self.setWindowTitle(os.path.basename(__file__)) # 'PyQT GUI with OpenCV and Picamera acquisition thread')
        self.move(300,100)
        screen = QDesktopWidget().availableGeometry()
        self.imageWidth = round(screen.height() * 0.8)
        self.imageHeight = round(screen.width() * 0.8)        
        # Labels
        self.PixImage = QLabel()
        self.procClockLabel = QLabel()
        # Buttons
        self.xLeftButton  = QPushButton("X left")
        self.xRightButton = QPushButton("X right")
        self.yLeftButton  = QPushButton("Y left")
        self.yRightButton = QPushButton("Y right")
        self.zUpButton    = QPushButton("Z up")
        self.zDownButton  = QPushButton("Z down")
        self.xLeftButton.setAutoRepeat(True)
        self.xRightButton.setAutoRepeat(True)
        self.yLeftButton.setAutoRepeat(True)
        self.yRightButton.setAutoRepeat(True)
        self.zUpButton.setAutoRepeat(True)
        self.zDownButton.setAutoRepeat(True)
        self.xLeftButton.setAutoRepeatDelay(0)
        self.xRightButton.setAutoRepeatDelay(0)
        self.yLeftButton.setAutoRepeatDelay(0)
        self.yRightButton.setAutoRepeatDelay(0)
        self.zUpButton.setAutoRepeatDelay(0)
        self.zDownButton.setAutoRepeatDelay(0)
        self.xLeftButton.setShortcut(Qt.Key_Left)
        self.xRightButton.setShortcut(Qt.Key_Right)
        self.yLeftButton.setShortcut(Qt.Key_Up)
        self.yRightButton.setShortcut(Qt.Key_Down)
        self.zUpButton.setShortcut(Qt.Key_Minus)
        self.zDownButton.setShortcut(Qt.Key_Plus)        
        # Compose layout grid
        widgetLayout = QGridLayout()
        widgetLayout.addWidget(self.xLeftButton,  0, 0, Qt.AlignLeft)
        widgetLayout.addWidget(self.xRightButton, 0, 1, Qt.AlignLeft)
        widgetLayout.addWidget(self.yLeftButton,  1, 0, Qt.AlignLeft)
        widgetLayout.addWidget(self.yRightButton, 1, 1, Qt.AlignLeft)
        widgetLayout.addWidget(self.zUpButton,    2, 0, Qt.AlignLeft)
        widgetLayout.addWidget(self.zDownButton,  2, 1, Qt.AlignLeft)
        widgetLayout.setSpacing(10)
        widgetLayout.addItem(QSpacerItem(0, 0, QSizePolicy.Minimum,QSizePolicy.Expanding))  # variable space
        # widgetLayout.addWidget(self.procClockLabel,index+1,0,alignment=Qt.AlignLeft)
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

    def wheelEvent(self, event):
        if (event.angleDelta().y() > 0) and (self.imageScalingFactor > self.imageScalingStep):  # zooming in
            self.imageScalingFactor -= self.imageScalingStep
        elif (event.angleDelta().y() < 0) and (self.imageScalingFactor < 1.0):  # zooming out
            self.imageScalingFactor += self.imageScalingStep        
        self.imageScalingFactor = round(self.imageScalingFactor, 2)  # strange behaviour, so rounding is necessary
        self.update()  # redraw the image with different scaling            

    def closeEvent(self, event: QCloseEvent):
        self.closing.emit()
        event.accept()

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

class GPIOEvent(QObject):
    name = "GPIOEvent"
    sigMsg = pyqtSignal(str)  # Message signal
    eventDetected = pyqtSignal(int, bool)  # Event signal

    def __init__(self, pins):
        super().__init__()
        GPIO.setmode(GPIO.BCM)  # set pin numbering mode
        for pin in pins:
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            GPIO.add_event_detect(pin, GPIO.BOTH, callback=lambda: self.my_callback(pin), bouncetime=200)

    def my_callback(self, pin):
        rising_edge = bool(GPIO.input(pin))
        if rising_edge:
            self.sigMsg.emit(self.name + ": rising edge detected on pin " + pin)
        else:
            self.sigMsg.emit(self.name + ": falling edge detected on pin " + pin)
        self.eventDetected.emit(pin, rising_edge)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    print("App started!")    
        
    # Instantiate objects
    logWindow = LogWindow()
    mainWindow = MainWindow()
    vs = PiVideoStream((WIDTH, HEIGHT), FRAME_RATE)
    myMotor = RpiMotorLib.BYJMotor()
    xLimitSwitch = GPIOEvent([X_limit_pin])    
##    myMotor = RpiMotorLib.A4988Nema(dir_pin, step_pin, MSR_pins, "A4988")
    vs.start()    
    
    # Connect signals and slots
    mainWindow.sigMsg.connect(logWindow.append)  # Log messages
    # myLimitSwitches.sigMsg.connect(logWindow.append)  # Log messages
    vs.sigMsg.connect(logWindow.append)  # Log messages
    vs.ready.connect(mainWindow.update)  # Stream images to main window
    
    # mainWindow.showProcStepCombo.currentIndexChanged.connect(imgProc.setProcStep)
    # mainWindow.invertBinary.stateChanged.connect(imgProc.setInvertBinary)
    # mainWindow.offsetSpinBox.valueChanged.connect(imgProc.setAdaptiveThresholdOffset)
##    mainWindow.Button.clicked.connect(lambda: myMotor.motor_go(clockwise=False, steptype="Full", steps=100, stepdelay=.01, verbose=False, initdelay=.05))
    mainWindow.xLeftButton.clicked.connect(lambda: myMotor.motor_run(gpiopins=X_motor_pins , wait=.001, steps=10, ccwise=False, steptype='half'))
    mainWindow.xRightButton.clicked.connect(lambda: myMotor.motor_run(gpiopins=X_motor_pins , wait=.001, steps=10, ccwise=True, steptype='half'))
    mainWindow.yLeftButton.clicked.connect(lambda: myMotor.motor_run(gpiopins=Y_motor_pins , wait=.001, steps=10, ccwise=True, steptype='half'))
    mainWindow.yRightButton.clicked.connect(lambda: myMotor.motor_run(gpiopins=Y_motor_pins , wait=.001, steps=10, ccwise=False, steptype='half'))
    mainWindow.zUpButton.clicked.connect(lambda: myMotor.motor_run(gpiopins=Z_motor_pins , wait=.001, steps=10, ccwise=False, steptype='half'))
    mainWindow.zDownButton.clicked.connect(lambda: myMotor.motor_run(gpiopins=Z_motor_pins , wait=.001, steps=10, ccwise=True, steptype='half'))
    mainWindow.closing.connect(logWindow.close)  # Close log window

    # Start the show
    logWindow.show()
    mainWindow.show()    
    app.exec_()
    GPIO.cleanup()  # good practise to cleanup GPIO at some point before exit
    
