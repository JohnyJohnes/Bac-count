#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
todo: implement homing, add auto well plate acquisition from Daan

"""
import os
import sys
import time
from datetime import datetime
import numpy as np
import cv2
from PySide2.QtCore import Qt, QObject, QThread, QTimer, Signal, Slot, QSettings, QEventLoop
from PySide2.QtCore import QSemaphore
from PySide2.QtWidgets import QWidget, QDesktopWidget, QApplication, QGridLayout, QHBoxLayout
from PySide2.QtWidgets import QVBoxLayout, QLabel, QSpacerItem, QSizePolicy, QPushButton
from PySide2.QtWidgets import QComboBox, QCheckBox, QTextEdit, QDoubleSpinBox, QSpinBox
from PySide2.QtGui import QCloseEvent, QPixmap, QImage
import pigpio
sys.path.append(r'../lib') # local libraries
from biorpi.pyqtpicam import PiVideoStream
from biorpi.log import LogWindow
from biorpi.dip import ImgEnhancer, ImgSegmenter, BlobDetector
from biorpi.af import AutoFocus
from biorpi.stepper_state import Stepper
from biorpi.stepper_calibrate import Stepper_Calibrate
current_milli_time = lambda: int(round(time.time() * 1000))
active_motors = QSemaphore(0)

class MainWindow(QWidget):
    name = "MainWindow"
    closing = Signal()  # Window closed signal.
    message = Signal(str)  # Message signal.
    snapshotrequest = Signal(str) # Request for snapshot.
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
        self.motorLabel = QLabel()
        self.imageQualityLabel = QLabel()
        
        # Buttons
        self.xLeftButton  = QPushButton("X left")
        self.xRightButton = QPushButton("X right")
        self.yLeftButton  = QPushButton("Y left")
        self.yRightButton = QPushButton("Y right")
        self.zUpButton    = QPushButton("Z up")
        self.zDownButton  = QPushButton("Z down")       
        self.xHomeButton  = QPushButton("X home")
        self.yHomeButton  = QPushButton("Y home")
        self.GoToButton = QPushButton("Go to")
        self.RetToButton = QPushButton("Return to")
        self.StopButton = QPushButton("STOP")
        self.snapshotButton = QPushButton("Snapshot")
        self.snapshotButton.clicked.connect(self.snapshot)
        self.calibrateButton = QPushButton("Calibrate")
        self.stopcalibrateButton = QPushButton("Stop calibrate")

        # Spinboxes
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
        
        # Spinboxes for movement
        self.xMovementSpinBox = QSpinBox(self)
        self.xMovementSpinBoxTitle = QLabel("X-move (.1mm)")
        self.xMovementSpinBox.setMinimum(-200000)
        self.xMovementSpinBox.setMaximum(200000)
        self.xMovementSpinBox.setSingleStep(1)
        self.xMovementSpinBox.setValue(0)
        self.yMovementSpinBox = QSpinBox(self)
        self.yMovementpinBoxTitle = QLabel("Y-move (.1mm)")
        self.yMovementSpinBox.setMinimum(-200000)
        self.yMovementSpinBox.setMaximum(200000)
        self.yMovementSpinBox.setSingleStep(1)
        self.yMovementSpinBox.setValue(0)
        
        # Compose layout grid
        self.keyVarWidgets = [self.gammaSpinBoxTitle, self.claheSpinBoxTitle, self.xMovementSpinBoxTitle, self.yMovementpinBoxTitle]
        self.valueVarWidgets = [self.gammaSpinBox, self.claheSpinBox, self.xMovementSpinBox, self.yMovementSpinBox]
        
        varWidgetLayout = QGridLayout()
        for index, widget in enumerate(self.keyVarWidgets):
            if widget is not None:
                varWidgetLayout.addWidget(widget, index, 0, Qt.AlignRight)
        for index, widget in enumerate(self.valueVarWidgets):
            if widget is not None:
                varWidgetLayout.addWidget(widget, index, 1, Qt.AlignRight)
        varWidgetLayout.addItem(QSpacerItem(0, 0, QSizePolicy.Minimum,QSizePolicy.Expanding))  # variable space
                
        widgetLayout = QGridLayout()
        widgetLayout.addWidget(self.xLeftButton,  0, 0, Qt.AlignRight)
        widgetLayout.addWidget(self.xRightButton, 0, 1, Qt.AlignLeft)
        widgetLayout.addWidget(self.yLeftButton,  1, 0, Qt.AlignRight)
        widgetLayout.addWidget(self.yRightButton, 1, 1, Qt.AlignLeft)
        widgetLayout.addWidget(self.zUpButton,    2, 0, Qt.AlignRight)
        widgetLayout.addWidget(self.zDownButton,  2, 1, Qt.AlignLeft)
        widgetLayout.addWidget(self.GoToButton,   3, 0, Qt.AlignRight)
        widgetLayout.addWidget(self.RetToButton,  3, 1, Qt.AlignLeft)
        widgetLayout.addWidget(self.xHomeButton,  4, 0, Qt.AlignRight)
        widgetLayout.addWidget(self.yHomeButton,  4, 1, Qt.AlignLeft)
        widgetLayout.addWidget(self.calibrateButton, 5,0, Qt.AlignRight)
        widgetLayout.addWidget(self.snapshotButton, 5,1, Qt.AlignLeft)
        widgetLayout.addWidget(self.StopButton, 6,0, Qt.AlignRight)
        widgetLayout.setSpacing(10)
        widgetLayout.addItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))  # variable space
        widgetLayout.addWidget(self.motorLabel,7,1,alignment=Qt.AlignLeft)
        widgetLayout.addWidget(self.imageQualityLabel,8,0,alignment=Qt.AlignRight)
        widgetLayout.addWidget(self.timerLabel,8,1,alignment=Qt.AlignLeft)

        layout = QHBoxLayout()
        layout.addLayout(varWidgetLayout, Qt.AlignTop|Qt.AlignCenter)
        layout.addLayout(widgetLayout, Qt.AlignTop|Qt.AlignCenter)
        layout.addWidget(self.PixImage, Qt.AlignTop|Qt.AlignCenter)
        self.setLayout(layout)


    @Slot(np.ndarray)
    def imgUpdate(self, image=None):
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
            cv2.line(image, (0, int(image.shape[0]*0.5)), (int(image.shape[1]), int(image.shape[0]*0.5)), 255, 1)
            cv2.line(image, (int(image.shape[1]*0.5), 0), (int(image.shape[1]*0.5), int(image.shape[1])), 255, 1)
            qImage = QImage(image.data, width, height, width * 3, QImage.Format_RGB888)  # Convert from OpenCV to PixMap
            self.PixImage.setPixmap(QPixmap(qImage))
            self.PixImage.show()

    @Slot()
    def kickTimer(self):
        clockTime = current_milli_time() # datetime.now()
        if self.prevClockTime is not None:
            timeDiff = clockTime - self.prevClockTime
            self.timerLabel.setText("Processing time: " + "{:04d}".format(round(timeDiff)) + " ms")
            self.motorLabel.setText("Active motors: " + str(active_motors.available()) )
            self.message.emit(self.name + ": processing delay = " + str(round(timeDiff)) + " ms")            
        self.prevClockTime = clockTime
    
    @Slot(str)        
    def log_calib(self, coordinates=None):
        if not(self.image is None):
            self.imgUpdate()
            filename = self.appName + '_' +  str(current_milli_time()) + '_'+   str(coordinates) + '.png'
            cv2.imwrite("./calibration_data/" + filename, self.image)
            logfile = open("./calibration_data/log.txt", "a")
            logfile.write(str(filename) + ', '+ str(coordinates)  + ',\n\r' )   
            logfile.close()
            self.message.emit(self.name + ": calibration image written to " + filename)
            
    def snapshot(self):
        if not(self.image is None):
            self.imgUpdate()
            filename = self.appName + '_'+ str(current_milli_time()) + '.png'
            cv2.imwrite(filename, self.image)
            self.message.emit(self.name + ": image written to " + filename)

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

    def loadSettings(self):
        self.message.emit(self.name + ": Loading settings from " + self.settings.fileName())
        for index, widget in enumerate(self.keyVarWidgets):  # retreive all labeled parameters
            if isinstance(widget, QLabel):
                if self.settings.contains(widget.text()):
                    self.valueVarWidgets[index].setValue(float(self.settings.value(widget.text())))

    def saveSettings(self):
        self.message.emit(self.name + ": Saving settings to " + self.settings.fileName())
        for index, widget in enumerate(self.keyVarWidgets):  # save all labeled parameters
            if isinstance(widget, QLabel):
                self.settings.setValue(widget.text(), self.valueVarWidgets[index].value())
        for index, widget in enumerate(self.valueVarWidgets):  # save all labeled parameters
            if isinstance(widget, QCheckBox):
                self.settings.setValue(widget.text(), widget.isChecked())
    
    def wait_Millisec(self, milliseconds):
        loop = QEventLoop()
        QTimer.singleShot(milliseconds, loop.exit)
        loop.exec_()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    print("App started!")
    settings = QSettings("settings.ini", QSettings.IniFormat)
        
    # Instantiate objects    
    logWindow = LogWindow()
    mainWindow = MainWindow()
    pio = pigpio.pi()
    pio.write(25, False) #positive wire
    pio.write(27, True) #negative wire
    M_Motor_X = Stepper(pio, int(settings.value("Motor_X/NEN_pin")), int(settings.value("Motor_X/DIR_pin")),
                       int(settings.value("Motor_X/STP_pin")), int(settings.value("Motor_X/LIM_pin")),
                       True, active_motors)
    M_Motor_Y = Stepper(pio, int(settings.value("Motor_Y/NEN_pin")), int(settings.value("Motor_Y/DIR_pin")),
                       int(settings.value("Motor_Y/STP_pin")), int(settings.value("Motor_Y/LIM_pin")),
                       False, active_motors)
    
    vs = PiVideoStream(resolution=(int(settings.value("camera/width")), int(settings.value("camera/height"))),
                       monochrome=True, framerate=int(settings.value("camera/framerate")),
                       effect='blur', use_video_port=bool(settings.value("camera/use_video_port")))
    
    calib = Stepper_Calibrate(M_Motor_X, M_Motor_Y, vs)
    vs.start()
    enhancer = ImgEnhancer()
    
    # Connect GUI signals and slots
    mainWindow.gammaSpinBox.valueChanged.connect(enhancer.setGamma)
    mainWindow.claheSpinBox.valueChanged.connect(enhancer.setClaheClipLimit)
    
    mainWindow.xLeftButton.pressed.connect(lambda: M_Motor_X.activate(clockwise=False))
    mainWindow.xLeftButton.released.connect(lambda: M_Motor_X.stop())
    mainWindow.xRightButton.pressed.connect(lambda: M_Motor_X.activate(clockwise=True))
    mainWindow.xRightButton.released.connect(lambda: M_Motor_X.stop())
    mainWindow.yLeftButton.pressed.connect(lambda: M_Motor_Y.activate(clockwise=False))
    mainWindow.yLeftButton.released.connect(lambda: M_Motor_Y.stop())
    mainWindow.yRightButton.pressed.connect(lambda: M_Motor_Y.activate(clockwise=True))
    mainWindow.yRightButton.released.connect(lambda: M_Motor_Y.stop())
    
    mainWindow.xHomeButton.clicked.connect(lambda: M_Motor_X.home())
    mainWindow.yHomeButton.clicked.connect(lambda: M_Motor_Y.home())
    mainWindow.RetToButton.clicked.connect(lambda: M_Motor_X.run( -(mainWindow.xMovementSpinBox.value()) ))
    mainWindow.RetToButton.clicked.connect(lambda: M_Motor_Y.run( -(mainWindow.yMovementSpinBox.value()) ))
    mainWindow.GoToButton.clicked.connect(lambda: M_Motor_Y.run( mainWindow.yMovementSpinBox.value() ))
    mainWindow.GoToButton.clicked.connect(lambda: M_Motor_X.run( mainWindow.xMovementSpinBox.value() ))
    
    mainWindow.StopButton.clicked.connect(lambda: M_Motor_X.stop())
    mainWindow.StopButton.clicked.connect(lambda: M_Motor_Y.stop())
    mainWindow.calibrateButton.clicked.connect(lambda: calib.run())
        
    # Connect processing signals and slots
    vs.ready.connect(mainWindow.kickTimer)  # Measure time delay    
    vs.ready.connect(lambda: enhancer.imgUpdate(vs.frame), type=Qt.BlockingQueuedConnection)  # Connect video/image stream to processing Qt.BlockingQueuedConnection or QueuedConnection?
    enhancer.ready.connect(lambda: mainWindow.imgUpdate(enhancer.image), type=Qt.QueuedConnection) # Stream images to main window

    # Log messages    
    M_Motor_X.message.connect(logWindow.append)
    M_Motor_Y.message.connect(logWindow.append)
    calib.message.connect(logWindow.append)
    
    # Snapshot requests
    calib.snapshotrequest.connect(mainWindow.log_calib)
    
    # Recipes invoked when mainWindow is closed, note that scheduler stops other threads
    mainWindow.closing.connect(logWindow.close)
    mainWindow.closing.connect(vs.stop)
    mainWindow.closing.connect(M_Motor_X.stop)
    mainWindow.closing.connect(M_Motor_Y.stop)
    mainWindow.closing.connect(calib.stop)
    
    # Start the show
    logWindow.show()
    mainWindow.show()    
    app.exec_()
    pio.stop()
    
