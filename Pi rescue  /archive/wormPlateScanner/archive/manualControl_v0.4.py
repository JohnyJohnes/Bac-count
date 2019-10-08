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
from biorpi.stepper_state import Stepper

current_milli_time = lambda: int(round(time.time() * 1000))

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
        self.xLeftButton  = QPushButton("X left")
        self.xRightButton = QPushButton("X right")
        self.yLeftButton  = QPushButton("Y left")
        self.yRightButton = QPushButton("Y right")
        self.zUpButton    = QPushButton("Z up")
        self.zDownButton  = QPushButton("Z down")
        self.xLeftButton.setShortcut(Qt.Key_Left)
        self.xRightButton.setShortcut(Qt.Key_Right)
        self.yLeftButton.setShortcut(Qt.Key_Down)
        self.yRightButton.setShortcut(Qt.Key_Up)
        self.zUpButton.setShortcut(Qt.Key_Minus)
        self.zDownButton.setShortcut(Qt.Key_Plus)        
        self.xHomeButton  = QPushButton("X home")
        self.yHomeButton  = QPushButton("Y home")
        self.GoToButton = QPushButton("Go to")
        self.RetToButton = QPushButton("Return to")
        self.StopButton = QPushButton("STOP")
        self.snapshotButton = QPushButton("Snapshot")
        self.snapshotButton.clicked.connect(self.snapshot)
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
        self.xMovementSpinBoxTitle = QLabel("X-move")
        self.xMovementSpinBox.setMinimum(-5000)
        self.xMovementSpinBox.setMaximum(5000)
        self.xMovementSpinBox.setSingleStep(10)
        self.xMovementSpinBox.setValue(0)
        self.yMovementSpinBox = QSpinBox(self)
        self.yMovementpinBoxTitle = QLabel("Y-move")
        self.yMovementSpinBox.setMinimum(-5000)
        self.yMovementSpinBox.setMaximum(5000)
        self.yMovementSpinBox.setSingleStep(10)
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
        widgetLayout.addWidget(self.snapshotButton, 5,1, Qt.AlignLeft)
        widgetLayout.addWidget(self.StopButton, 5,0, Qt.AlignRight)
        widgetLayout.setSpacing(10)
        widgetLayout.addItem(QSpacerItem(0, 0, QSizePolicy.Minimum,QSizePolicy.Expanding))  # variable space
        widgetLayout.addWidget(self.imageQualityLabel,5,0,alignment=Qt.AlignLeft)
        widgetLayout.addWidget(self.timerLabel,6,0,alignment=Qt.AlignLeft)

        layout = QHBoxLayout()
        layout.addLayout(varWidgetLayout, Qt.AlignTop|Qt.AlignCenter)
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
                
            cv2.rectangle(image, (int(image.shape[1]*.25), int(image.shape[0]*.25)), (int(image.shape[1]*.75), int(image.shape[0]*.75)), 255, 1)
            
            cv2.line(image, (0, int(image.shape[0]*0.5)), (int(image.shape[1]), int(image.shape[0]*0.5)), 255, 1)
            cv2.line(image, (int(image.shape[1]*0.5), 0), (int(image.shape[1]*0.5), int(image.shape[1])), 255, 1)
            
            qImage = QImage(image.data, width, height, width * 3, QImage.Format_RGB888)  # Convert from OpenCV to PixMap
            self.PixImage.setPixmap(QPixmap(qImage))
            self.PixImage.show()

    @pyqtSlot()
    def kickTimer(self):
        clockTime = current_milli_time() # datetime.now()
        if self.prevClockTime is not None:
            timeDiff = clockTime - self.prevClockTime
            self.timerLabel.setText("Processing time: " + "{:04d}".format(round(timeDiff)) + " ms")
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


if __name__ == '__main__':
    app = QApplication(sys.argv)
    print("App started!")
    settings = QSettings("settings.ini", QSettings.IniFormat)
        
    # Instantiate objects
    vs = PiVideoStream(resolution=(int(settings.value("camera/width")), int(settings.value("camera/height"))),
                       monochrome=True, framerate=int(settings.value("camera/framerate")),
                       effect='blur', use_video_port=bool(settings.value("camera/use_video_port")))
    vs.start()    
    logWindow = LogWindow()
    mainWindow = MainWindow()
    enhancer = ImgEnhancer()
##    segmenter = ImgSegmenter(doPlot=False)
##    detector = BlobDetector(doPlot=False)
    pio = pigpio.pi()
    myXMotor = Stepper(pio, int(settings.value("xMotor/X_NEN_pin")), int(settings.value("xMotor/X_DIR_pin")),
                       int(settings.value("xMotor/X_STP_pin")), int(settings.value("xMotor/X_LIM_pin")))
    myYMotor = Stepper(pio, int(settings.value("yMotor/Y_NEN_pin")), int(settings.value("yMotor/Y_DIR_pin")),
                       int(settings.value("yMotor/Y_STP_pin")), int(settings.value("yMotor/Y_LIM_pin")))
    
    # Connect GUI signals and slots
    mainWindow.gammaSpinBox.valueChanged.connect(enhancer.setGamma)
    mainWindow.claheSpinBox.valueChanged.connect(enhancer.setClaheClipLimit)
    mainWindow.xLeftButton.pressed.connect(lambda: myXMotor.step(clockwise=False))
    mainWindow.xLeftButton.released.connect(lambda: myXMotor.stop())
    mainWindow.xRightButton.pressed.connect(lambda: myXMotor.step(clockwise=True))
    mainWindow.xRightButton.released.connect(lambda: myXMotor.stop())
    mainWindow.yLeftButton.pressed.connect(lambda: myYMotor.step(clockwise=False))
    mainWindow.yLeftButton.released.connect(lambda: myYMotor.stop())
    mainWindow.yRightButton.pressed.connect(lambda: myYMotor.step(clockwise=True))
    mainWindow.yRightButton.released.connect(lambda: myYMotor.stop())    
    mainWindow.xHomeButton.clicked.connect(lambda: myXMotor.home())
    mainWindow.yHomeButton.clicked.connect(lambda: myYMotor.home())
    mainWindow.RetToButton.clicked.connect(lambda: myXMotor.run( -(mainWindow.xMovementSpinBox.value()) ))
    mainWindow.RetToButton.clicked.connect(lambda: myYMotor.run( -(mainWindow.yMovementSpinBox.value()) ))
    mainWindow.GoToButton.clicked.connect(lambda: myXMotor.run( mainWindow.xMovementSpinBox.value() ))
    mainWindow.StopButton.clicked.connect(lambda: myXMotor.stop())
    mainWindow.StopButton.clicked.connect(lambda: myYMotor.stop())
    
        
    # Connect processing signals and slots
    vs.ready.connect(mainWindow.kickTimer)  # Measure time delay    
    vs.ready.connect(lambda: enhancer.imgUpdate(vs.frame), type=Qt.BlockingQueuedConnection)  # Connect video/image stream to processing Qt.BlockingQueuedConnection or QueuedConnection?
    enhancer.ready.connect(lambda: mainWindow.imgUpdate(enhancer.image), type=Qt.QueuedConnection) # Stream images to main window
##    enhancer.ready.connect(lambda: segmenter.start(enhancer.image), type=Qt.QueuedConnection) # Get enhanced image from object
##    segmenter.ready.connect(lambda: detector.start(segmenter.image, segmenter.ROIs), type=Qt.QueuedConnection)  # Stream RoIs to blobdetector
##    segmenter.ready.connect(lambda: mainWindow.imageQualityLabel.setText("Image quality: " + "{:.4f}".format(segmenter.imgQuality)))  # display image quality
    
    # Log messages    
##    mainWindow.message.connect(logWindow.append)
##    vs.message.connect(logWindow.append)
##    enhancer.message.connect(logWindow.append)
##    segmenter.message.connect(logWindow.append)
##    detector.message.connect(logWindow.append)
    myXMotor.message.connect(logWindow.append)
    myYMotor.message.connect(logWindow.append)
    
    # Recipes invoked when mainWindow is closed, note that scheduler stops other threads
    mainWindow.closing.connect(logWindow.close)
    mainWindow.closing.connect(vs.stop)
    mainWindow.closing.connect(myXMotor.stop)
    mainWindow.closing.connect(myYMotor.stop)
    
    # Start the show
    logWindow.show()
    mainWindow.show()    
    app.exec_()
    pio.stop()
    
