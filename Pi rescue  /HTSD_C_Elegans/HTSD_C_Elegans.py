#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os, sys, time, datetime
import cv2, pigpio
import numpy as np

from PySide2.QtCore import *
from PySide2.QtWidgets import *
from PySide2.QtGui import *

from lib.PiCam import *
from lib.Logger import LogWindow
from lib.ImageProcessing import *
from lib.Stepper import *

current_milli_time = lambda: int(round(time.time() * 1000))
active_motors = QSemaphore(0)

class MainWindow(QWidget):
	name = "MainWindow"
	closing = Signal()  # Window closed signal.
	message = Signal(str)  # Message signal.
	snapshotrequest = Signal(str) # Request for snapshot.
	image = None
	ThreadList = []
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
		widgetLayout.addWidget(self.GoToButton,   3, 0, Qt.AlignRight)
		widgetLayout.addWidget(self.RetToButton,  3, 1, Qt.AlignLeft)
		widgetLayout.addWidget(self.xHomeButton,  4, 0, Qt.AlignRight)
		widgetLayout.addWidget(self.yHomeButton,  4, 1, Qt.AlignLeft)
		widgetLayout.addWidget(self.calibrateButton, 5,0, Qt.AlignRight)
		widgetLayout.addWidget(self.snapshotButton, 5,1, Qt.AlignLeft)
		widgetLayout.addWidget(self.StopButton, 6,0, Qt.AlignRight)
		widgetLayout.addWidget(self.motorLabel,7,0,alignment=Qt.AlignRight)
		widgetLayout.addWidget(self.timerLabel,8,0,alignment=Qt.AlignRight)
		widgetLayout.setSpacing(10)
		widgetLayout.addItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))  # variable space
		
		layout = QHBoxLayout()
		layout.addLayout(varWidgetLayout, Qt.AlignTop|Qt.AlignCenter)
		layout.addLayout(widgetLayout, Qt.AlignTop|Qt.AlignCenter)
		layout.addWidget(self.PixImage, Qt.AlignTop|Qt.AlignCenter)
		self.setLayout(layout)
		self.move(400,50)

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
			#cv2.line(image, (0, int(image.shape[0]*0.5)), (int(image.shape[1]), int(image.shape[0]*0.5)), 255, 1)
                        #cv2.line(image, (int(image.shape[1]*0.5), 0), (int(image.shape[1]*0.5), int(image.shape[1])), 255, 1)
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
	    for n in range(0, milliseconds, 1):
                loop = QEventLoop()
                QTimer.singleShot(1, loop.exit)
                loop.exec_()

if __name__ == '__main__':
	app = QApplication(sys.argv)
	print("App started!")
	settings = QSettings("settings.ini", QSettings.IniFormat)
		
	# Instantiate objects   
	logWindow = LogWindow()
	mainWindow = MainWindow()
	GPIO = pigpio.pi()
	GPIO.write(22, False) #positive wire
	GPIO.write(7, True) #negative wire
	VideoStream = PiVideoStream(resolution=(int(settings.value("camera/width")), int(settings.value("camera/height"))), monochrome=True, framerate=int(settings.value("camera/framerate")), effect='blur', use_video_port=bool(settings.value("camera/use_video_port")))
	VideoStream.start()
	ImageEnhance = ImgEnhancer()
	Stepper_Motor_X = Stepper_Control(GPIO, int(settings.value("Motor_X/NEN_pin")), int(settings.value("Motor_X/DIR_pin")), int(settings.value("Motor_X/STP_pin")), int(settings.value("Motor_X/LIM_pin")), True, active_motors)
	Stepper_Motor_Y = Stepper_Control(GPIO, int(settings.value("Motor_Y/NEN_pin")), int(settings.value("Motor_Y/DIR_pin")), int(settings.value("Motor_Y/STP_pin")), int(settings.value("Motor_Y/LIM_pin")), False, active_motors)
	Stepper_Calibrator = Stepper_Calibrate(Stepper_Motor_X, Stepper_Motor_Y, VideoStream)
	ThreadList = [VideoStream, ImageEnhance, Stepper_Motor_X, Stepper_Motor_Y, Stepper_Calibrator]	
	
	# Connect GUI signals and slots
	mainWindow.gammaSpinBox.valueChanged.connect(ImageEnhance.setGamma)
	mainWindow.claheSpinBox.valueChanged.connect(ImageEnhance.setClaheClipLimit)
	
	mainWindow.xLeftButton.pressed.connect(lambda: Stepper_Motor_X.activate(clockwise=False))
	mainWindow.xLeftButton.released.connect(lambda: Stepper_Motor_X.stop())
	mainWindow.xRightButton.pressed.connect(lambda: Stepper_Motor_X.activate(clockwise=True))
	mainWindow.xRightButton.released.connect(lambda: Stepper_Motor_X.stop())
	mainWindow.yLeftButton.pressed.connect(lambda: Stepper_Motor_Y.activate(clockwise=False))
	mainWindow.yLeftButton.released.connect(lambda: Stepper_Motor_Y.stop())
	mainWindow.yRightButton.pressed.connect(lambda: Stepper_Motor_Y.activate(clockwise=True))
	mainWindow.yRightButton.released.connect(lambda: Stepper_Motor_Y.stop())
	
	mainWindow.xHomeButton.clicked.connect(lambda: Stepper_Motor_X.home())
	mainWindow.yHomeButton.clicked.connect(lambda: Stepper_Motor_Y.home())
	mainWindow.RetToButton.clicked.connect(lambda: Stepper_Motor_X.run( -(mainWindow.xMovementSpinBox.value()) ))
	mainWindow.RetToButton.clicked.connect(lambda: Stepper_Motor_Y.run( -(mainWindow.yMovementSpinBox.value()) ))
	mainWindow.GoToButton.clicked.connect(lambda: Stepper_Motor_Y.run( mainWindow.yMovementSpinBox.value() ))
	mainWindow.GoToButton.clicked.connect(lambda: Stepper_Motor_X.run( mainWindow.xMovementSpinBox.value() ))
	mainWindow.calibrateButton.clicked.connect(lambda: Stepper_Calibrator.run())
	mainWindow.StopButton.clicked.connect(lambda: Stepper_Motor_X.stop())
	mainWindow.StopButton.clicked.connect(lambda: Stepper_Motor_Y.stop())
	mainWindow.StopButton.clicked.connect(lambda: Stepper_Calibrator.stop())
	
	# Connect processing signals and slots
	VideoStream.ready.connect(mainWindow.kickTimer)  # Measure time delay   
	VideoStream.ready.connect(lambda: ImageEnhance.imgUpdate(VideoStream.frame), type=Qt.BlockingQueuedConnection)  # Connect video/image stream to processing Qt.BlockingQueuedConnection or QueuedConnection?
	ImageEnhance.ready.connect(lambda: mainWindow.imgUpdate(ImageEnhance.image), type=Qt.QueuedConnection) # Stream images to main window

	# Log messages  
	Stepper_Motor_X.message.connect(logWindow.append)
	Stepper_Motor_Y.message.connect(logWindow.append)
	Stepper_Calibrator.message.connect(logWindow.append)
	
	# Snapshot requests
	Stepper_Calibrator.snapshotrequest.connect(mainWindow.log_calib)
	
	# Recipes invoked when mainWindow is closed, note that scheduler stops other threads
	mainWindow.closing.connect(logWindow.close)
	mainWindow.closing.connect(VideoStream.close)	
	mainWindow.closing.connect(ImageEnhance.close)	
	mainWindow.closing.connect(Stepper_Calibrator.close)
	mainWindow.closing.connect(Stepper_Motor_X.close)
	mainWindow.closing.connect(Stepper_Motor_Y.close)
	
	# Start the show
	logWindow.show()
	mainWindow.show()   
	app.exec_()
	
	# Wait for threads to exit.
	for Threads in ThreadList:
		Threads.wait(100)
		
	# Stop GPIO. 
	GPIO.stop()
	
		

	
