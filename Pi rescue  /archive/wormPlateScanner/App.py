#!/usr/bin/env python
import sys
from PyQt4 import QtGui, QtCore
import pigpio
import time 
from Components import PWM, Stopbutton

pi = pigpio.pi()

gpiomotor = [[14,15,18,23],[24,25,8,7],[4,17,27,22]]

Motor = PWM(pi,gpiomotor)

EndstopX = Stopbutton(pi,21)
EndstopY = Stopbutton(pi,2)
EndstopZ = Stopbutton(pi,3)

current_milli_time = lambda: int(round(time.time()*1000))

        
if not pi.connected:
  exit(0)

class Window(QtGui.QMainWindow):
    
    def __init__(self):
        super(Window, self).__init__()
        self.setGeometry(50, 50, 500, 300)
        self.setWindowTitle("PyQt first")
        #self.setWindowIcon(QtGui.GIcon('pythonlogo.png'))
        
        #main menu
        extractAction = QtGui.QAction("GET TO THE CHOPPER", self)
        extractAction.setShortcut("Ctrl+Q")
        extractAction.setStatusTip('Leave The App')
        extractAction.triggered.connect(self.close_application)
        
        self.statusBar()
        
        mainMenu = self.menuBar()
        fileMenu = mainMenu.addMenu('&File')
        fileMenu.addAction(extractAction)
        
        self.home()
        
    def home(self):
        btn = QtGui.QPushButton("Quit", self)
        btn.clicked.connect(self.close_application)
        btn.resize(100, 100)
        btn.move(0, 100)
        
        btn2 = QtGui.QPushButton("Start", self)
        btn2.clicked.connect(self.homeing)
        btn2.resize(100, 100)
        btn2.move(100, 100)
        
        btn3 = QtGui.QPushButton("Kill", self)
        btn3.clicked.connect(self.kill)
        btn3.resize(100, 100)
        btn3.move(200, 100)
        
        btn4 = QtGui.QPushButton("<", self)
        self.add_button_attributes(btn4, 30, 30, 200, 200, press = (lambda: Motor.activate(1, -1, update = True)), release = (self.kill))
        
        btn5 = QtGui.QPushButton(">", self)
        self.add_button_attributes(btn5, 30, 30, 250, 200, press = (lambda: Motor.activate(1, 1, update = True)), release = (self.kill))
        
        extractAction = QtGui.QAction(QtGui.QIcon("ICON"), "Flee the Scene", self)
        extractAction.triggered.connect(self.close_application)
        
        self.toolBar = self.addToolBar("Extraction")
        self.toolBar.addAction(extractAction)
        
        checkBox = QtGui.QCheckBox('Enlarge Window', self)
        checkBox.move(100,25)
        checkBox.resize(100, 100)
        checkBox.toggle()
        checkBox.stateChanged.connect(self.enlarge_window)
        
        self.show()

    def add_button_attributes(self, name, sizex, sizey, posx, posy, press = None, release = None):
        if release is not None:
            name.pressed.connect(press)
        if release is not None:
            name.released.connect(release)
        name.resize(sizex, sizey)
        name.move(posx, posy)
        
    def enlarge_window(self, state):
        if state == QtCore.Qt.Checked:
            self.setGeometry(50,50,1000,600)
        else:
            self.setGeometry(50,50,500,300)
    
    
    def homeing(self):
        Motor.activate(0, -1)
        Motor.activate(1, 1)
        Motor.activate(2, 1)
        Motor.update()
        
        x = current_milli_time() + 10000
        
        
        while x > current_milli_time():
            if EndstopX.read() == 0:
                Motor.deactivate(0)
            if EndstopY.read() == 0:
                Motor.deactivate(1)
            if EndstopZ.read() == 0:
                Motor.deactivate(2)
        print("get out")      
                
    def kill(self):
        Motor.deactivate(0)
        Motor.deactivate(1)
        Motor.deactivate(2)

    def close_application(self):
        choice = QtGui.QMessageBox.question(self, 'Extract!', "Get out?", QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)        
        
        if choice == QtGui.QMessageBox.Yes:
            sys.exit()
        else:
            pass


def run():
    app = QtGui.QApplication(sys.argv)
    GUI = Window()
    sys.exit(app.exec_())

run()

