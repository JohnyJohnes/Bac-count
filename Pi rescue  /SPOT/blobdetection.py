#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
PyQT GUI with OpenCV for image processing of microscope images
TODO:
- T-API support?
- open directory and save settings to dirname
- process file one by one: open first image to set all parameters, then process Buttons
Author: Jeroen Veen
"""

import os
import glob
import sys
import cv2
import numpy as np
from PyQt5.QtCore import (Qt, pyqtSignal, pyqtSlot, QSettings)
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QComboBox,
                             QGridLayout, QLabel, QFileDialog, QDesktopWidget,
                             QSpinBox, QDoubleSpinBox, QCheckBox)
from PyQt5.QtGui import QPixmap, QImage
from LogImageData import LogImageData
from ImageProcessing import ImageProcessing
# from random import randint
# from matplotlib import pyplot as plt
# from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
# from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
# from matplotlib.figure import Figure


class MainWindow(QWidget):
    newFile = pyqtSignal(str)
    newImage = pyqtSignal(np.ndarray)

    def __init__(self):
        super().__init__()
        self.cwd = os.getcwd()
        self.settings = QSettings(
            self.cwd + "\\" + os.path.basename(__file__) + "settings.ini", QSettings.IniFormat)
        self.listDir = None
        self.image = None
        self.imageScalingFactor = 1.0
        self.imageScalingStep = 0.1
        self.imageProcessing = ImageProcessing()
        self.title = "Blob detection"
        self.initUI()

    def initUI(self):
        self.center()
        self.setWindowTitle(self.title)
        self.layout = QGridLayout()
        screen = QDesktopWidget().availableGeometry()
        self.imageWidth = round(screen.height() * 0.7)
        self.imageHeight = round(screen.width() * 0.7)
        # Labels
        self.PixImage = QLabel()
        # Buttons
        self.openButton = QPushButton("Open")
        self.openButton.clicked.connect(self.openFolder)  # Image)
        self.nextButton = QPushButton("Next")
        self.nextButton.clicked.connect(self.nextImage)

        # Combos
        self.showProcStepCombo = QComboBox(self)
        self.showProcStepCombo.addItem("Original")
        self.showProcStepCombo.addItem("Gray")
        self.showProcStepCombo.addItem("Filtered")
        self.showProcStepCombo.addItem("BW")
        # Checkboxes
        self.showAnnotated = QCheckBox("Annot")
        self.showAnnotated.setChecked(True)
        self.invertBinary = QCheckBox("Invert")
        # Spinboxes
        self.rotateSpinBox = QDoubleSpinBox(self)
        self.rotateSpinBoxTitle = QLabel("rotate")
        self.rotateSpinBox.setSuffix("°")
        self.rotateSpinBox.setMinimum(-5.0)
        self.rotateSpinBox.setMaximum(5.0)
        self.rotateSpinBox.setSingleStep(0.1)
        self.blurSpinBox = QSpinBox(self)
        self.blurSpinBoxTitle = QLabel("ksize")
        self.blurSpinBox.setMinimum(3)
        self.blurSpinBox.setSingleStep(2)
        self.blocksizeSpinBox = QSpinBox(self)
        self.blocksizeSpinBoxTitle = QLabel("blocksize")
        self.blocksizeSpinBox.setMinimum(3)
        self.blocksizeSpinBox.setSingleStep(2)
        self.offsetSpinBoxTitle = QLabel("offset")
        self.offsetSpinBox = QSpinBox(self)
        self.offsetSpinBox.setMinimum(-5)
        self.offsetSpinBox.setMaximum(5)
        self.gridSmoothSpinBox = QSpinBox(self)
        self.gridSmoothSpinBoxTitle = QLabel("gridSmooth")
        self.gridSmoothSpinBox.setMinimum(3)
        self.gridSmoothSpinBox.setSingleStep(2)
        self.gridMinSegmentLengthSpinBox = QSpinBox(self)
        self.gridMinSegmentLengthSpinBoxTitle = QLabel("minSegmentLength")
        self.gridMinSegmentLengthSpinBox.setMinimum(1)
        self.minBlobAreaSpinBox = QSpinBox(self)
        self.minBlobAreaSpinBoxTitle = QLabel("minBlobArea")
        self.minBlobAreaSpinBox.setMinimum(10)
        self.minBlobAreaSpinBox.setMaximum(1000)
        self.cropXp1Spinbox = QSpinBox(self)
        self.cropXp1SpinboxTitle = QLabel("xp1")
        self.cropXp1Spinbox.setMinimum(0)
        self.cropXp1Spinbox.setMaximum(1000)
        self.cropXp1Spinbox.setSingleStep(10)
        self.cropXp2Spinbox = QSpinBox(self)
        self.cropXp2SpinboxTitle = QLabel("xp2")
        self.cropXp2Spinbox.setMinimum(self.cropXp1Spinbox.value())
        self.cropXp2Spinbox.setMaximum(5000)
        self.cropXp2Spinbox.setSingleStep(10)
        self.cropXp2Spinbox.setValue(self.imageHeight)
        self.cropXp2Spinbox.setSingleStep(10)
        self.cropYp1Spinbox = QSpinBox(self)
        self.cropYp1SpinboxTitle = QLabel("yp1")
        self.cropYp1Spinbox.setMinimum(0)
        self.cropYp1Spinbox.setMaximum(1000)
        self.cropYp1Spinbox.setSingleStep(10)
        self.cropYp2Spinbox = QSpinBox(self)
        self.cropYp2SpinboxTitle = QLabel("yp2")
        self.cropYp2Spinbox.setMinimum(self.cropYp1Spinbox.value())
        self.cropYp2Spinbox.setMaximum(5000)
        self.cropYp2Spinbox.setSingleStep(10)
        self.cropYp2Spinbox.setValue(self.imageHeight)
        # Compose layout grid
        self.keyWidgets = [self.openButton, self.nextButton, None, self.rotateSpinBoxTitle,
                           self.cropXp1SpinboxTitle, self.cropYp1SpinboxTitle, self.cropXp2SpinboxTitle, self.cropYp2SpinboxTitle,
                           self.blurSpinBoxTitle, self.blocksizeSpinBoxTitle, self.offsetSpinBoxTitle, self.gridSmoothSpinBoxTitle,
                           self.gridMinSegmentLengthSpinBoxTitle, self.minBlobAreaSpinBoxTitle]

        self.valueWidgets = [self.showProcStepCombo, self.showAnnotated,            self.invertBinary,                     self.rotateSpinBox,
                             self.cropXp1Spinbox,    self.cropYp1Spinbox,           self.cropXp2Spinbox,                   self.cropYp2Spinbox,
                             self.blurSpinBox,       self.blocksizeSpinBox,         self.offsetSpinBox,                    self.gridSmoothSpinBox,
                             self.gridMinSegmentLengthSpinBox,       self.minBlobAreaSpinBox]

        for index, widget in enumerate(self.keyWidgets):
            if widget is not None:
                self.layout.addWidget(widget, 0, index, Qt.AlignCenter)
        for index, widget in enumerate(self.valueWidgets):
            if widget is not None:
                self.layout.addWidget(widget, 1, index, Qt.AlignCenter)
        self.layout.addWidget(self.PixImage, 2, 0, 25, 25, Qt.AlignCenter)
        self.setLayout(self.layout)
        self.showMaximized()

    def loadSettings(self):
        for index, widget in enumerate(self.keyWidgets):  # retreive all labeled parameters
            if isinstance(widget, QLabel):
                if self.settings.contains(widget.text()):
                    self.valueWidgets[index].setValue(float(self.settings.value(widget.text())))

    def center(self):
        qr = self.frameGeometry()
        screen = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(screen)
        self.move(qr.topLeft())

    def wheelEvent(self, event):
        if (event.angleDelta().y() > 0) and (self.imageScalingFactor > self.imageScalingStep):  # zooming in
            self.imageScalingFactor -= self.imageScalingStep
        elif (event.angleDelta().y() < 0) and (self.imageScalingFactor < 1.0):  # zooming out
            self.imageScalingFactor += self.imageScalingStep
        # strange behaviour, so rounding is necessary
        self.imageScalingFactor = round(self.imageScalingFactor, 2)
        self.updateImage()  # redraw the image with different scaling

    def openFolder(self, fdir=False):
        if not fdir:
            fdir = QFileDialog.getExistingDirectory(
                self, "Select Folder", self.cwd, QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks)
        if fdir:
            self.cwd = fdir  # os.path.dirname(fname[0])
            self.settings = QSettings(
                self.cwd + "\\" + os.path.basename(__file__) + "settings.ini", QSettings.IniFormat)
            self.loadSettings()
            # included_extensions = ['tif', 'bmp', 'png', 'gif']
            self.listDir = glob.glob(self.cwd + '\*.png')
            self.curFileNr = 0
            # randint(0, len(self.listDir) - 1)]  # open a random file
            self.fname = self.listDir[self.curFileNr]
            image = cv2.imread(self.fname, cv2.IMREAD_COLOR)
            self.newFile.emit(self.fname)
            self.newImage.emit(image)

    def openImage(self, fname=False):
        if not fname:
            fname = QFileDialog.getOpenFileName(
                self, 'Open file', self.cwd, "Image files (*.tif *.png *.jpg *.gif)")
        if fname[0]:
            self.cwd = os.path.dirname(fname[0])
            self.settings = QSettings(
                self.cwd + "\\" + os.path.basename(__file__) + "settings.ini", QSettings.IniFormat)
            self.loadSettings()
            image = cv2.imread(fname[0], cv2.IMREAD_COLOR)
            self.newFile.emit(fname[0])
            self.newImage.emit(image)

    def nextImage(self):
        self.curFileNr = self.curFileNr + 1 if self.curFileNr < len(self.listDir) - 1 else 0
        self.fname = self.listDir[self.curFileNr]
        image = cv2.imread(self.fname, cv2.IMREAD_COLOR)
        self.newFile.emit(self.fname)
        self.newImage.emit(image)

    def closeEvent(self, event):
        for index, widget in enumerate(self.keyWidgets):  # save all labeled parameters
            if isinstance(widget, QLabel):
                self.settings.setValue(widget.text(), self.valueWidgets[index].value())
        for index, widget in enumerate(self.valueWidgets):  # save all labeled parameters
            if isinstance(widget, QCheckBox):
                self.settings.setValue(widget.text(), widget.isChecked())
        event.accept()

    @pyqtSlot(np.ndarray)
    def updateImage(self, image=None):
        if not(image is None):  # we have a new image
            self.image = image
        else:  # continue with old image
            image = self.image
        if not(image is None):
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
            self.qImage = QImage(image.data, width, height, width * 3, QImage.Format_RGB888)
            self.pixmap = QPixmap(self.qImage)
            self.PixImage.setPixmap(self.pixmap)
            self.PixImage.show()
            self.qImage = QImage(image, width, height, 3 * width,
                                 QImage.Format_RGB888)  # Convert from OpenCV to PixMap


if __name__ == '__main__':
    app = QApplication(sys.argv)
    # Instantiate objects
    mainWindow = MainWindow()
    imageProcessing = ImageProcessing()
    logImageData = LogImageData()
    # Connect signals and slots
    mainWindow.showProcStepCombo.currentIndexChanged.connect(imageProcessing.setProcStep)
    mainWindow.showAnnotated.stateChanged.connect(imageProcessing.setAnnotate)
    mainWindow.rotateSpinBox.valueChanged.connect(imageProcessing.setRotateAngle)
    mainWindow.cropXp1Spinbox.valueChanged.connect(imageProcessing.setCropXp1)
    mainWindow.cropYp1Spinbox.valueChanged.connect(imageProcessing.setCropYp1)
    mainWindow.cropXp2Spinbox.valueChanged.connect(imageProcessing.setCropXp2)
    mainWindow.cropYp2Spinbox.valueChanged.connect(imageProcessing.setCropYp2)
    mainWindow.blurSpinBox.valueChanged.connect(imageProcessing.setMedianBlurKsize)
    mainWindow.blocksizeSpinBox.valueChanged.connect(imageProcessing.setAdaptiveThresholdBlocksize)
    mainWindow.offsetSpinBox.valueChanged.connect(imageProcessing.setAdaptiveThresholdOffset)
    mainWindow.invertBinary.stateChanged.connect(imageProcessing.setInvertBinary)
    mainWindow.gridSmoothSpinBox.valueChanged.connect(imageProcessing.setGridSmoothKsize)
    mainWindow.gridMinSegmentLengthSpinBox.valueChanged.connect(
        imageProcessing.setGridMinSegmentLength)
    mainWindow.minBlobAreaSpinBox.valueChanged.connect(imageProcessing.setMinBlobArea)
    mainWindow.newImage.connect(imageProcessing.start)
    imageProcessing.ready.connect(mainWindow.updateImage)
    imageProcessing.ready.connect(logImageData.start)
    mainWindow.newFile.connect(logImageData.setFilename)
    # start the show
    mainWindow.show()
    mainWindow.loadSettings()
    # finish
#    print(cv2.getBuildInformation())
    sys.exit(app.exec_())
