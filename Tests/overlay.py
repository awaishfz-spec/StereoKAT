# -*- coding: utf-8 -*-
"""

"""

import math, sys

from PyQt4 import QtCore, QtGui
#from PyQt4.QtCore import Qt, QTimer, QRectF
#from PyQt4.QtGui import *
import numpy as np
import time

class Overlay(QtGui.QWidget):

    def __init__(self, speed = 18, parent = None):
    
        super(Overlay, self).__init__(parent)
        palette = QtGui.QPalette(self.palette())
        palette.setColor(palette.Background, QtCore.Qt.transparent)
        self.setPalette(palette)
        
        self.theta_start = 90
        self.theta = 0 #Specifies straight up
        self.radius = 50
        self.speed = speed 
        self.colorList = [QtGui.QColor(16, 159, 221), QtGui.QColor(221,89,2)]
        
           
    def paintEvent(self, event):
    
        painter = QtGui.QPainter()
        painter.begin(self)
        
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.fillRect(event.rect(), QtGui.QBrush(QtGui.QColor(255, 255, 255, 50)))
        painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
                
        painter.setBrush(QtGui.QBrush(self.colorList[0]))
                
        painter.drawEllipse(self.width()/2 - self.radius, self.height() / 2 - self.radius, self.radius*2, self.radius*2)
        
        #painter.setPen(QPen(QColor(255,0,0)))
        painter.setBrush(QtGui.QBrush(self.colorList[1]))
                
        pieRect = QtCore.QRectF(self.width()/2 - self.radius, self.height() / 2 - self.radius, self.radius*2, self.radius*2)
        painter.drawPie(pieRect, self.theta_start*16, -self.theta*16)
#        painter.drawLine(self.width()/2 , self.height() / 2, self.width() / 2 + np.sin(self.theta) * self.radius,  self.height()/2.0 + np.cos(self.theta) * self.radius)
#        painter.drawLine(self.width()/2, self.height()/2, 50,50 )
        painter.end()
    
    def showEvent(self, event):
    
        self.timer = self.startTimer(50)
        
    def timerEvent(self, event):
    
       
        self.theta += self.speed
        
        if self.theta > 360:
            self.theta = 0
            self.colorList.reverse()
        
        print(self.theta)
        self.update()
    
    def endTimer(self):
        
        self.killTimer(self.timer)
        self.hide()


class MainWindow(QtGui.QMainWindow):

    def __init__(self, parent = None):
    
        QtGui.QMainWindow.__init__(self, parent)
        
        widget = QtGui.QWidget(self)
        self.editor = QtGui.QTextEdit()
        self.editor.setPlainText("0123456789"*100)
        layout = QtGui.QGridLayout(widget)
        layout.addWidget(self.editor, 0, 0, 1, 3)
        button = QtGui.QPushButton("Wait")
        layout.addWidget(button, 1, 1, 1, 1)
        
        self.setCentralWidget(widget)
        self.overlay = Overlay(speed = 15, parent = self.centralWidget())        
        
        button.clicked.connect(self.overlay.show)    
      
    def resizeEvent(self, event):
    
        self.overlay.resize(event.size())
        event.accept()


if __name__ == "__main__":

    app = QtGui.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())