#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
PyQT GUI with OpenCV for image processing

Author: Jeroen Veen
"""
import os
import sys
import cv2
from PyQt5 import Qt
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QGridLayout, QLabel,QFileDialog
from PyQt5.QtGui import QPixmap, QImage

#from matplotlib import pyplot as plt
#from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
#from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
#from matplotlib.figure import Figure


class mainWindow(QWidget):

    def __init__(self):
        super().__init__()
        self.title = "QPixMapRender"
        self.left = 100
        self.top = 100
        self.width = 320
        self.height = 100
        self.initUI()
 
    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        layout = QGridLayout()
        self.label = QLabel()

        openButton = QPushButton("Open")
        openButton.clicked.connect(self.openImage)
        
        layout.addWidget(self.label, 0, 0, 1, 3, Qt.Qt.AlignCenter)
        layout.addWidget(openButton, 2, 0, Qt.Qt.AlignLeft)

        self.setLayout(layout)
        self.show()
        
    def openImage(self):
        fname = QFileDialog.getOpenFileName(self, 'Open file',os.getcwd(),"Image files (*.tif *.png *.jpg *.gif)")
        if fname[0]:
            self.cvImage = cv2.imread(fname[0], cv2.IMREAD_COLOR)
            self.updateImage()

    def updateImage(self):
        """
        Convert from OpenCV to PixMap 
        """
        height, width, nrOfChannels = self.cvImage.shape
        cv2.cvtColor(self.cvImage, cv2.COLOR_BGR2RGB, self.cvImage)
        self.qImage = QImage(self.cvImage.data, width, height, nrOfChannels*width, QImage.Format_RGB888)
        self.pixmap = QPixmap(self.qImage)        
        self.label.setPixmap(self.pixmap)            
#        self.label.show()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    mw = mainWindow()
    mw.resize(600,400)
    sys.exit(app.exec_())
