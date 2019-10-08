#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
PyQT GUI for manual control of WormPlateScanner EPS_v2 (A4988 Stepper Motor Driver)
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
from picamera import PiCamera
from picamera.array import PiRGBArray, PiYUVArray
import pigpio

## define motor driver pins
X_NEN_pin = 14
X_STP_pin = 15
X_DIR_pin = 18
X_LIM_pin = 0

Y_NEN_pin = 23
Y_STP_pin = 24
Y_DIR_pin = 25
Y_LIM_pin = 0

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

##class GPIOEvent(QObject):
##    name = "GPIOEvent"
##    sigMsg = pyqtSignal(str)  # Message signal
##    eventDetected = pyqtSignal(int, bool)  # Event signal
##
##    def __init__(self, pins):
##        super().__init__()
##        GPIO.setmode(GPIO.BCM)  # set pin numbering mode
##        for pin in pins:
##            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
##            GPIO.add_event_detect(pin, GPIO.BOTH, callback=lambda: self.my_callback(pin), bouncetime=200)
##
##    def my_callback(self, pin):
##        rising_edge = bool(GPIO.input(pin))
##        if rising_edge:
##            self.sigMsg.emit(self.name + ": rising edge detected on pin " + pin)
##        else:
##            self.sigMsg.emit(self.name + ": falling edge detected on pin " + pin)
##        self.eventDetected.emit(pin, rising_edge)
##

class Stepper(QObject):
# Stepper Motor Driver (A4988/DRV8825)
## inspired by
##  https://github.com/laurb9/StepperDriver (https://github.com/laurb9/StepperDriver/blob/master/src/BasicStepperDriver.cpp)
##  https://www.rototron.info/raspberry-pi-stepper-motor-tutorial/
##  https://raspberrypi.stackexchange.com/questions/74313/pigpio-wave-chaining-count-total-pulses-sent
# TODO:
#  make sure the standard direction drives the load towards the end-stop
#  s-curve ramp up/down
#  function that drives exactly N steps, with s-curve, using self.cbc.tally()??
#  (implement MS_pins)
#  do something with the limit switch: interrupt + call-back
#  homing function
#
    sigMsg = pyqtSignal(str)  # Message signal
    pio = None # Reference to PigPIO object
    motor_type = "A4988"
    NEN_pin  = None # not Enable
    DIR_pin = None
    STP_pin = None
    LIM_pin = None
    MS_pins = (None, None, None)
    running = False  # flag indicating whether the motor is running
    pulse_count = 0  # pulse counter (from home)

    def __init__(self, pio, NEN_pin=14, DIR_pin=15, STP_pin=18, LIM_pin=0, MS_pins=(1,2,3)):
        super().__init__()
        if not isinstance(pio, pigpio.pi):
            raise TypeError("Constructor attribute is not a pigpio.pi instance!")
        if not(0<=NEN_pin<=26) or not(0<=DIR_pin<=26) or not (0<=STP_pin<=26) or not (0<=LIM_pin<=26):
            raise Error("Constructor attributes are not GPIO pin numbers!")
        self.NEN_pin  = NEN_pin
        self.DIR_pin = DIR_pin
        self.STP_pin = STP_pin
        self.LIM_pin = LIM_pin
        self.MS_pins = MS_pins
        self.pio = pio
        self.pio.set_mode(self.NEN_pin, pigpio.OUTPUT)
        self.pio.write(self.NEN_pin, True) # inverse logic
        self.pio.set_mode(self.DIR_pin, pigpio.OUTPUT)
        self.pio.write(self.DIR_pin, False)
##        for i in self.MS_pins:
##            self.pio.set_mode(i, pigpio.OUTPUT)
        self.pio.set_mode(self.STP_pin, pigpio.OUTPUT)
        self.pio.write(self.STP_pin, False)
        self.cbc = self.pio.callback(self.STP_pin)  # to create a simple "callback counter" on the pin where the PWM pulses are sent

    @pyqtSlot(float)
    def go(self, clockwise=False, steptype="Full"):
        try:
            if not(self.pio is None):
                if not self.running:
                    self.sigMsg.emit(self.__class__.__name__ + ": go on pins (" + str(self.NEN_pin)+","+ str(self.DIR_pin)+","+str(self.STP_pin)+")")
                    self.running = True
                    self.setResolution(steptype)
                    self.pio.write(self.NEN_pin, False) # inverse logic
                    self.pio.write(self.DIR_pin, clockwise) # DIR pin is sampled on rising STEP edge, so it is set first
                    self.generate_ramp([
                                        [7,  0],
                                        [20, 0],
                                        [57, 1],
                                        [154,1],
                                        [354,1],
                                        [622,1],
                                        [832,1],
                                        [937,1],
                                        [978,1],
                                        [993,1]
                                        ]) # sigmoid ramp up
                    self.pio.set_PWM_frequency(self.STP_pin, 1000)
                    self.pio.set_PWM_dutycycle(self.STP_pin, 128) # PWM 3/4 on
        except Exception as err:
            raise ValueError(self.__class__.__name__ + ": ValueError")
                             
    def cbf(gpio, level, tick):
       print(gpio, level, tick)
       self.stop()
       self.sigMsg.emit(self.__name__ + ": home!")

    @pyqtSlot(float)
    def home(self, clockwise=False, steptype="Full"):
##        cb1 = self.pio.callback(user_gpio=self.LIM_pin, func=self.cbf)
        self.go(clockwise=clockwise, steps=int(1e4)) ## Run until limit switch is hit
        print(self.cbc.tally()) # to display number of pulses made
        self.cbc.reset_tally() # to reset the counter
    
    @pyqtSlot()
    def stop(self):
        if self.running:
            self.sigMsg.emit(self.__class__.__name__ + ": stop on pins (" + str(self.NEN_pin)+","+ str(self.DIR_pin)+","+str(self.STP_pin)+")")
            try:
                if not(self.pio is None):
                    self.pio.set_PWM_frequency(self.STP_pin,0)
                    self.generate_ramp([[993,1],
                                        [979,1],
                                        [937,1],
                                        [832,1],
                                        [622,1],
                                        [354,1],
                                        [154,1],
                                        [57, 1],
                                        [20, 0],
                                        [7,  0]
                                        ]) # sigmoid rampdown
                    self.pio.write(self.NEN_pin, True) # inverse logic
                    self.running = False            
                    self.sigMsg.emit(self.__class__.__name__ + ": Current number of steps is " + str(self.cbc.tally())) # to display number of pulses made                    
            except Exception as err:
                self.sigMsg.emit(self.__class__.__name__ + ": Error")

    def setResolution(self, steptype):
        """ method to calculate step resolution
        based on motor type and steptype"""
        if self.motor_type == "A4988":
            resolution = {'Full': (0, 0, 0),
                          'Half': (1, 0, 0),
                          '1/4': (0, 1, 0),
                          '1/8': (1, 1, 0),
                          '1/16': (1, 1, 1)}
        elif self.motor_type == "DRV8825":
            resolution = {'Full': (0, 0, 0),
                          'Half': (1, 0, 0),
                          '1/4': (0, 1, 0),
                          '1/8': (1, 1, 0),
                          '1/16': (0, 0, 1),
                          '1/32': (1, 0, 1)}
        else: 
            raise ValueError("Error invalid motor_type: {}".format(steptype))
##        self.pio.write(self.MS_pins, resolution[steptype])

    def generate_ramp(self, ramp):
        """Generate ramp wave forms.
        ramp:  List of [Frequency, Steps]
        """
        self.pio.wave_clear()     # clear existing waves
        length = len(ramp)  # number of ramp levels
        wid = [-1] * length

        # Generate a wave per ramp level
        for i in range(length):
            frequency = ramp[i][0]
            micros = int(500000 / frequency)
            wf = []
            wf.append(pigpio.pulse(1 << self.STP_pin, 0, micros))  # pulse on
            wf.append(pigpio.pulse(0, 1 << self.STP_pin, micros))  # pulse off
            self.pio.wave_add_generic(wf)
            wid[i] = self.pio.wave_create()

        # Generate a chain of waves
        chain = []
        for i in range(length):
            steps = ramp[i][1]
            x = steps & 255
            y = steps >> 8
            chain += [255, 0, wid[i], 255, 1, x, y]

        self.pio.wave_chain(chain)  # Transmit chain.
        # Is this required?
        while self.pio.wave_tx_busy(): # While transmitting.
            time.sleep(0.1)
        # delete all waves
        for i in range(length):
            self.pio.wave_delete(wid[i])

          
           

if __name__ == '__main__':
    app = QApplication(sys.argv)
    print("App started!")    
        
    # Instantiate objects
    logWindow = LogWindow()
    mainWindow = MainWindow()
    vs = PiVideoStream((WIDTH, HEIGHT), FRAME_RATE)
    pio = pigpio.pi()
    myXMotor = Stepper(pio, NEN_pin=X_NEN_pin, DIR_pin=X_DIR_pin, STP_pin=X_STP_pin)
    myYMotor = Stepper(pio, NEN_pin=Y_NEN_pin, DIR_pin=Y_DIR_pin, STP_pin=Y_STP_pin)
##        def __init__(self, pio, NEN_pin=14, DIR_pin=15, STP_pin=18, LIM_pin=0, MS_pins=(1,2,3)):

##
##    xLimitSwitch = GPIOEvent([X_limit_pin])    
    vs.start()    
    
    # Connect signals and slots
    mainWindow.sigMsg.connect(logWindow.append)  # Log messages
    # myLimitSwitches.sigMsg.connect(logWindow.append)  # Log messages
    vs.sigMsg.connect(logWindow.append)  # Log messages
    vs.ready.connect(mainWindow.update)  # Stream images to main window
    
    # mainWindow.showProcStepCombo.currentIndexChanged.connect(imgProc.setProcStep)
    # mainWindow.invertBinary.stateChanged.connect(imgProc.setInvertBinary)
    # mainWindow.offsetSpinBox.valueChanged.connect(imgProc.setAdaptiveThresholdOffset)
    mainWindow.xLeftButton.pressed.connect(lambda: myXMotor.go(clockwise=False))
    mainWindow.xLeftButton.released.connect(lambda: myXMotor.stop())
    mainWindow.xRightButton.pressed.connect(lambda: myXMotor.go(clockwise=True))
    mainWindow.xRightButton.released.connect(lambda: myXMotor.stop())
    mainWindow.yLeftButton.pressed.connect(lambda: myYMotor.go(clockwise=False))
    mainWindow.yLeftButton.released.connect(lambda: myYMotor.stop())
    mainWindow.yRightButton.pressed.connect(lambda: myYMotor.go(clockwise=True))
    mainWindow.yRightButton.released.connect(lambda: myYMotor.stop())
##    mainWindow.zUpButton.pressed.connect(lambda: myXMotor.activate(2, 1, update = True))
##    mainWindow.zUpButton.released.connect(lambda: myXMotor.deactivate(2))
##    mainWindow.zDownButton.pressed.connect(lambda: myXMotor.activate(2, -1, update = True))
##    mainWindow.zDownButton.released.connect(lambda: myXMotor.deactivate(2))
    mainWindow.closing.connect(logWindow.close)  # Close log window
    myXMotor.sigMsg.connect(logWindow.append)  # Log messages
    myYMotor.sigMsg.connect(logWindow.append)  # Log messages
    
    # Start the show
    logWindow.show()
    mainWindow.show()    
    app.exec_()
    pio.stop()
##    GPIO.cleanup()  # good practise to cleanup GPIO at some point before exit
    
