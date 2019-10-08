 #!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
"""

from PyQt5.QtWidgets import QWidget, QDialog, QApplication, QPushButton, QVBoxLayout, QDoubleSpinBox, QGridLayout, QSizePolicy
from PyQt5.QtGui import QPainter
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import sys
import random

class Window(QDialog):
    def __init__(self, parent=None):
        super(Window, self).__init__(parent)

        # a figure instance to plot on
        self.figure = plt.figure()

        # this is the Canvas Widget that displays the `figure`
        # it takes the `figure` instance as a parameter to __init__
        self.canvas = FigureCanvas(self.figure)

        # this is the Navigation widget
        # it takes the Canvas widget and a parent
        self.toolbar = NavigationToolbar(self.canvas, self)

        # Just some button connected to `plot` method
        self.button = QPushButton('Plot')
        self.button.clicked.connect(self.plot)

        # set the layout
        layout = QVBoxLayout()
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        layout.addWidget(self.button)
        self.setLayout(layout)

    def plot(self):
        ''' plot some random stuff '''
        # random data
        data = [random.random() for i in range(10)]

        # instead of ax.hold(False)
        self.figure.clear()

        # create an axis
        ax = self.figure.add_subplot(111)

        # discards the old graph
        # ax.hold(False) # deprecated, see above

        # plot data
        ax.plot(data, '*-')

        # refresh canvas
        self.canvas.draw()

if __name__ == '__main__':
    app = QApplication(sys.argv)

    main = Window()
    main.show()

    sys.exit(app.exec_())

    
##class Example(QWidget):
##
##    def __init__(self):
##        super().__init__()
##        self.rotateSpinBox = QDoubleSpinBox(self)
##        self.rotateSpinBox.valueChanged.connect(self.update)
##        self.layout = QGridLayout()
##        
        
##        self.rotateSpinBox.setMinimum(-5.0)
##        self.rotateSpinBox.setMaximum(5.0)
##        self.rotateSpinBox.setSingleStep(0.1)        

##        self.initUI()
##
##    def initUI(self):
##
##        self.setGeometry(300, 300, 500, 500)
##        self.setWindowTitle('Points')
##        self.rotateSpinBox.setSuffix("°")
##        self.layout.addWidget(self.rotateSpinBox, 1, 1, Qt.AlignTop|Qt.AlignLeft)
##        self.setLayout(self.layout)
##
##        m = PlotCanvas(self, width=5, height=4)
##        m.move(0,0)        
##        
##        self.show()
##
##    def paintEvent(self, e):
##        qp = QPainter()
##        qp.begin(self)
##        self.drawPoints(qp)
##        qp.end()
##
####    def update(self):
####        qp = QPainter()
####        qp.begin(self)
####        self.drawPoints(qp)
####        qp.end()        
##
##    def drawPoints(self, qp):
##
##        qp.setPen(Qt.red)
##        size = self.size()
##
##        for i in range(1000):
##            x = random.randint(1, size.width() - 1)
##            y = random.randint(1, size.height() - 1)
##            qp.drawPoint(x, y)
##
##
##class PlotCanvas(FigureCanvas):
## 
##    def __init__(self, parent=None, width=5, height=4, dpi=100):
##        fig = Figure(figsize=(width, height), dpi=dpi)
##        self.axes = fig.add_subplot(111)
## 
##        FigureCanvas.__init__(self, fig)
##        self.setParent(parent)
## 
##        FigureCanvas.setSizePolicy(self,
##                QSizePolicy.Expanding,
##                QSizePolicy.Expanding)
##        FigureCanvas.updateGeometry(self)
##        self.plot()
## 
## 
##    def plot(self):
##        data = [random.random() for i in range(25)]
##        ax = self.figure.add_subplot(111)
##        ax.plot(data, 'r-')
##        self.draw()
##        
##
##if __name__ == '__main__':
##
##    app = QApplication(sys.argv)
##    ex = Example()
##    sys.exit(app.exec_())
