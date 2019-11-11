# CameraClient2.py

import webbrowser


def saveData(data, filename):
    file = open(filename, "wb")
    file.write(data)
    file.close()


def display(data):
    jpgFile = "/Desktop/test.jpg"
    saveData(data, jpgFile)
    webbrowser.open(jpgFile)
