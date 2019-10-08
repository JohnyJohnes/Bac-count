#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
PyQT GUI for steppermotor control processing thread
Using https://github.com/gavinlyonsrepo/RpiMotorLib
"""
import os
import sys
import time
from datetime import datetime
import numpy as np
from PyQt5.QtCore import Qt, QObject, QThread, QTimer, pyqtSignal, pyqtSlot, QSettings
from PyQt5.QtWidgets import QWidget, QDesktopWidget, QApplication, QGridLayout, QHBoxLayout, QVBoxLayout
from PyQt5.QtWidgets import QLabel, QSpacerItem, QSizePolicy, QPushButton, QComboBox, QCheckBox, QTextEdit, QDoubleSpinBox, QSpinBox
from PyQt5.QtGui import QCloseEvent, QPixmap, QImage
import RPi.GPIO as GPIO
from RpiMotorLib import RpiMotorLib
    
#define GPIO pins
MSR_pins = (14, 15, 18)  # Microstep Resolution MS1-MS3
dir_pin = 20  # Direction
step_pin = 21  # Step
limit_pins = (23, 24)  # Limit switches
        
class MainWindow(QWidget):
    name = "MainWindow"
    closing = pyqtSignal()  # Window closed signal 
    sigMsg = pyqtSignal(str)  # Message signal

    def __init__(self):
       super().__init__()
       self.cwd = os.getcwd()
       self.settings = QSettings(self.cwd + "/" + os.path.basename(__file__) + "settings.ini", QSettings.IniFormat)
       self.initUI()
       self.loadSettings()       

    def initUI(self):
        self.setWindowTitle('PyQT GUI with OpenCV and Picamera acquisition thread')
        self.move(300,100)
        # screen = QDesktopWidget().availableGeometry()
        # self.imageWidth = round(screen.height() * 0.8)
        # self.imageHeight = round(screen.width() * 0.8)        
        # Labels
        # self.PixImage = QLabel()
        # self.procClockLabel = QLabel()
        # Buttons
        self.button = QPushButton("Button1")
        # Compose layout grid
        self.keyWidgets = [None]
        self.valueWidgets = [self.button]
        widgetLayout = QGridLayout()
        for index, widget in enumerate(self.keyWidgets):
            if widget is not None:
                widgetLayout.addWidget(widget, index, 0, Qt.AlignLeft)
        for index, widget in enumerate(self.valueWidgets):
            if widget is not None:
                widgetLayout.addWidget(widget, index, 1, Qt.AlignLeft)
        widgetLayout.setSpacing(10)
        widgetLayout.addItem(QSpacerItem(0, 0, QSizePolicy.Minimum,QSizePolicy.Expanding))  # variable space
        # widgetLayout.addWidget(self.procClockLabel,index+1,0,alignment=Qt.AlignLeft)
        layout = QHBoxLayout()
        layout.addLayout(widgetLayout, Qt.AlignTop|Qt.AlignCenter)
        # layout.addWidget(self.PixImage, Qt.AlignTop|Qt.AlignCenter)
        layout.setSpacing(10)
        self.setLayout(layout)

    def closeEvent(self, event: QCloseEvent):
        self.saveSettings()
        self.closing.emit()
        event.accept()

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
    myMotor = RpiMotorLib.A4988Nema(dir_pin, step_pin, MSR_pins, "A4988")
    myLimitSwitches = GPIOEvent(limit_pins)
    
    # Connect signals and slots
    mainWindow.sigMsg.connect(logWindow.append)  # Log messages
    # myLimitSwitches.sigMsg.connect(logWindow.append)  # Log messages

    # mainWindow.showProcStepCombo.currentIndexChanged.connect(imgProc.setProcStep)
    # mainWindow.invertBinary.stateChanged.connect(imgProc.setInvertBinary)
    # mainWindow.offsetSpinBox.valueChanged.connect(imgProc.setAdaptiveThresholdOffset)
    mainWindow.button.clicked.connect(lambda: myMotor.motor_go(clockwise=False, steptype="Full", steps=100, stepdelay=.01, verbose=False, initdelay=.05))
    mainWindow.closing.connect(logWindow.close)  # Close log window

    # Start the show
    logWindow.show()
    mainWindow.show()    
    app.exec_()
    GPIO.cleanup()  # good practise to cleanup GPIO at some point before exit
    
