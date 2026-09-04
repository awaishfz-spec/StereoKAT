# -*- coding: utf-8 -*-
"""
"""

import matplotlib.pylab as plt
import collections, calendar, time
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
import seaborn as sns
import os
import scipy.stats as sts
import numpy as np
import sys

if getattr(sys, 'frozen', False):
   base_path = sys._MEIPASS   
else:   
   base_path = os.path.dirname(os.path.realpath(sys.argv[0]))

try:
   from PySide import QtGui, QtCore
   Signal = QtCore.Signal
   Slot = QtCore.Slot
    
#   from PyQt4 import QtCore, QtGui  #Note that some code will need to be changed if this is used (Signal has different call signiture)
#   Signal = QtCore.pyqtSignal
#   Slot = QtCore.pyqtSlot
    
   onDesktop = False
    
except ImportError as exp:
    print(exp)
    print("Looking for PyQT")

    from PyQt4 import QtCore, QtGui  #Note that some code will need to be changed if this is used (Signal has different call signiture)
    Signal = QtCore.pyqtSignal
    Slot = QtCore.pyqtSlot
    
    onDesktop = True

    

class cameraSystemDialog(QtGui.QDialog):
    """A Dialog box which allows the user to cancel the connection between the two cameras"""
    def __init__(self, parent):
        
        super(cameraSystemDialog, self).__init__(parent)
        
        self.setObjectName("CameraSystemDialog")
        self.setWindowTitle("PSAT")
        self.setModal(True) #Lock focus on this widget

#        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        
        self.masterLayout = QtGui.QVBoxLayout()
        
        main_label = QtGui.QLabel("Welcome to PSAT")
        self.masterLayout.addWidget(main_label)
        
        self.masterLayout.addSpacing(20)
        
        sub_label = QtGui.QLabel("Please wait a moment for PSAT to start communicating with the cameras")
        sub_label.setStyleSheet("""font-size: 15px""")
        self.masterLayout.addWidget(sub_label)
        
        self.masterLayout.addSpacing(20)
        sub_label2 = QtGui.QLabel("If you want to use PSAT without the cameras click cancel")
        sub_label2.setStyleSheet("""font-size: 15px""")
        self.masterLayout.addWidget(sub_label2)
        
        self.masterLayout.addSpacing(20)
        self.masterLayout.addLayout(self.create_buttons())
        
        self.masterLayout.setAlignment(main_label, QtCore.Qt.AlignCenter)
        self.masterLayout.setAlignment(sub_label, QtCore.Qt.AlignCenter)
        self.masterLayout.setAlignment(sub_label2, QtCore.Qt.AlignCenter)
        
        self.setLayout(self.masterLayout)
       
        self.show()
        
    def create_buttons(self):
        
        buttonLayout = QtGui.QHBoxLayout()
                
        self.CloseButton = QtGui.QPushButton("Cancel")
        self.CloseButton.clicked.connect(self.close)
        
        buttonLayout.addWidget(self.CloseButton)
        
        return buttonLayout
        
    @Slot()
    def camerasLive(self):
        """Recivies a signal when the cameras go live and then starts a close down sequence"""
        print("SHUTTING CAMERA DIALOG")
        self.changeButtonText()

        QtGui.QApplication.processEvents() #Update the button
        t0 = time.time()
        
        while True:
            
            t1 = time.time() - t0
            
            if t1 > 1.5:
                
                self.close()
                break 
                
    def changeButtonText(self):
        
        self.CloseButton.setEnabled(False)
        self.CloseButton.setText("Cameras are live")
        self.CloseButton.setStyleSheet("""background: rgb(16, 159, 221)""")
        
        
    
class myDateLineEdit(QtGui.QLineEdit):
    """A QLineEdit for displaying the DOB. On click it should load a window to select a DOB"""
    
    clicked = Signal()
    
    def __init__(self):
        
        super(myDateLineEdit, self).__init__()
        self.setReadOnly(True)
        self.setText("DD/MM/YYYY")
        
    def mousePressEvent(self, e):
        
#        print("DOB Pressed")
#        self.setStyleSheet("""background-color: rgb(255,105,); """)
        self.clicked.emit()
        super(myDateLineEdit, self).mousePressEvent(e)
        
    def mouseReleaseEvent(self, e):
        
#        self.setStyleSheet("""background-color: rgb(52,50,52);""")    
        super(myDateLineEdit, self).mouseReleaseEvent(e)
        
    def reset_date(self):
        
        self.setText("DD/MM/YYYY")
      
    
class myDateDialog(QtGui.QDialog):
    """A diaglog widget to get DOB information"""
    
    def __init__(self, parent_window = None):
        
        super(myDateDialog, self).__init__()
        
        self.setObjectName("MyDateDialog")
        self.setWindowTitle("Select DOB")
    
#        self.setGeometry(100, 100, 10, 10)
    
#        self.setFixedSize(600, 360) #Do not allow the window to resize   
#        self.move(10,10)
        self.setModal(True) #Window will be locked in focus
        
        self.decade = 2000 #Decade the calendar will start on
        
        self.selectMonth()
        
        self.cal = calendar.Calendar(0) #Create a calendar object
        
        
        self.masterWidget = QtGui.QWidget()
        self.masterWidget.setObjectName("MyDOB")
        self.masterLayout = QtGui.QGridLayout()
        
        self.selectMonth() #Create Month window
        self.masterLayout.addWidget(self.monthView, 0, 0, 1, 1)
        
        self.selectYear()
        self.masterLayout.addWidget(self.yearView, 0, 0, 1, 1)
        self.yearView.hide()
        
        
     
        self.setLayout(self.masterLayout)
        
        self.setStyleSheet("""  QDialog {background: rgb(52,50,52)}
                                QLabel {border: 0px; color: rgb(221, 89, 2); font-family: embrima; font-size: 22px; font-weight: 500;}
                                QPushButton {background: rgb(52,50,52); border: 1px solid rgb(34, 85, 96); color: rgb(255, 255, 255);
                                             font-family: embrima; font-size: 20px; font-weight: 500; padding: 8px;} 
                                QToolButton {background: rgb(52,50,52); border: 1px solid rgb(34, 85, 96); color: rgb(255, 255, 255); padding: 8px;}
                           """)
        

        
    def selectMonth(self):
        
        self.monthView = QtGui.QWidget()
        
        masterLayout = QtGui.QVBoxLayout()
        
        myLayout = QtGui.QGridLayout()
        
        instruct1 = QtGui.QLabel("Select a month")
        instruct1.setAlignment(QtCore.Qt.AlignCenter)
        masterLayout.addWidget(instruct1)
        
        self.months = {'January': 1, 'February': 2, 'March': 3, 'April': 4, 'May': 5, 'June': 6, 'July': 7, 'August': 8, 'September': 9, 'October': 10, 'November': 11, 'Decemeber': 12}
        self.months = collections.OrderedDict(sorted(self.months.items(), key=lambda t: t[1]))

        month_labels = [key for key in self.months]
#        print(month_labels)
        self.buttons = []

        i = 0
        for row in range(3):
            for col in range(4):     
        
                button = QtGui.QPushButton(month_labels[i])
                button.clicked.connect(self.setMonth)
            
                myLayout.addWidget(button, row, col, 1, 1)
                self.buttons.append(button)
                i += 1
        
        masterLayout.addLayout(myLayout)
        self.monthView.setLayout(masterLayout)
        
    def setMonth(self):
        
        sender = self.sender()
        
        self.month_value = self.months[sender.text()]
        
#        print(sender.text(), self.months[sender.text()])
        
        self.monthView.hide()
        self.yearView.show()
        
    def selectYear(self):
        
        self.yearView = QtGui.QWidget()
        
        
        masterLayout = QtGui.QVBoxLayout()
        myLayout = QtGui.QGridLayout()
        
        instruct2 = QtGui.QLabel("Select a year")
        instruct2.setAlignment(QtCore.Qt.AlignCenter)
        masterLayout.addWidget(instruct2)
        
        
             
        display_years = range(self.decade, self.decade + 10)
        
        self.yearButtons = []
        i = 0
        for row in range(2):
            for col in range(5):
                
                button = QtGui.QPushButton(str(display_years[i]))
                button.clicked.connect(self.setYear)
                self.yearButtons.append(button)
                myLayout.addWidget(button, row, col, 1, 1)
                i += 1
        
        prev_button = QtGui.QToolButton()
        prev_button.setArrowType(QtCore.Qt.LeftArrow)
        prev_button.setObjectName("prev_decade")
        prev_button.clicked.connect(self.selectYearChangeDecade)
        
        next_button = QtGui.QToolButton()
        next_button.setArrowType(QtCore.Qt.RightArrow)
        next_button.setObjectName("next_decade")
        next_button.clicked.connect(self.selectYearChangeDecade)
   
        next_prevLayout = QtGui.QHBoxLayout()
        next_prevLayout.addWidget(prev_button)
        next_prevLayout.addWidget(next_button)
        
         
        masterLayout.addLayout(myLayout)
        masterLayout.addSpacing(8)
        masterLayout.addLayout(next_prevLayout)
        self.yearView.setLayout(masterLayout)
    
    def selectYearChangeDecade(self):
        
        sender = self.sender().objectName()
        
#        print(sender)
        
        if sender == 'next_decade':
            
            self.decade = self.decade + 10
            
            self.updateYearButtons()
        
        elif sender == "prev_decade":
            
            self.decade = self.decade - 10
            self.updateYearButtons()
            
    def updateYearButtons(self):
        
        display_years = range(self.decade, self.decade + 10)        

        i = 0
        for row in range(2):
            for col in range(5):               
              
                self.yearButtons[i].setText(str(display_years[i]))
                i += 1
      
    def setYear(self):
        
        sender = self.sender()
        
        self.year_value = sender.text()

        self.yearView.hide()
        
        self.selectDay()
        self.masterLayout.addWidget(self.dayView, 0, 0, 1, 1)
        self.dayView.show()

    def selectDay(self):
        
        self.dayView = QtGui.QWidget()
        
        myLayout = QtGui.QGridLayout()
        
        masterLayout = QtGui.QVBoxLayout()    
        
        instruct3 = QtGui.QLabel("Select a day")
        instruct3.setAlignment(QtCore.Qt.AlignCenter)
        masterLayout.addWidget(instruct3)
        
        cal = calendar.Calendar(0)
        days = [i for i in cal.itermonthdays(int(self.year_value), int(self.month_value)) if i != 0] #Get all the days in the month

        row = 0
        col = 0
        
        for d in range(len(days)):
            
             button = QtGui.QPushButton(str(days[d]))
             button.clicked.connect(self.setDay)
             
             myLayout.addWidget(button, row, col, 1, 1)
             
             col += 1
             
             if col > 4:
                 row +=1
                 col = 0
                 
        masterLayout.addLayout(myLayout)
        self.dayView.setLayout(masterLayout)
        
        
    def setDay(self):
        
        sender = self.sender()
        self.day_value = sender.text()        
       
        self.close()
        
        
    def save(self):
        """Save the result"""        
        
        self.DOB = '{}/{}/{}'.format(self.day_value, self.month_value, self.year_value)
        
        return self.DOB
        
        
    def showEvent(self, event):
        
        geom = self.frameGeometry()
        geom.moveCenter(QtGui.QCursor.pos())
          
        self.setGeometry(geom)
        super(myDateDialog, self).showEvent(event)
#        print("SHOWING")
        
    
                

class recordingLocLabel(QtGui.QLabel):
    """A scrolling label to show where the data is being stored"""
    
    def __init__(self, speed):
        
        super(recordingLocLabel, self).__init__()
        
        self.speed = speed
        
        self.setMinimumSize(300, 25)
        
        self.textPosOffset = 0
        
        self.qp = QtGui.QPainter()
        
        self.font_metrics = QtGui.QFontMetrics(self.qp.font())        

        self.standard_message = "No save directory has been set: Insert a USB and set the save directory"  
        self.message = self.standard_message
              
        self.record_message = False
    def paintEvent(self, e):
           
        self.qp.begin(self)
        self.drawWidget(self.qp)
        self.qp.end()   
          
    def drawWidget(self, qp):
      
#        font = QtGui.QFont('Serif', 7, QtGui.QFont.Light)
#        qp.setFont(font)

        size = self.size()
        w = size.width()
        h = size.height()    
        
         
        pen = QtGui.QPen(QtGui.QColor(52,50,52), 1)        
        qp.setPen(pen)        
        qp.setBrush(QtGui.QColor(52,50,52))
        qp.drawRect(0, 0, w, h)
#        qp.drawText()
        pen = QtGui.QPen(QtGui.QColor(255,255,255), 1)
        qp.setPen(pen)  
        qp.drawText( w - self.textPosOffset, h-5, self.message)
    
    def scrollText(self):
        
        pixelsWide = 2* self.font_metrics.width(self.message)
        
        self.textPosOffset += 1 * self.speed
        
        if self.textPosOffset > (pixelsWide):
            self.textPosOffset = 0
        self.repaint()
        
    def setMessage(self, message):
        """Set a new message"""
        
        if message == '':
            self.message = self.standard_message
        else:
            
            self.message = "Recording directory: {}".format(message)            
            self.textPosOffset = 0
             
    
class positionLabel(QtGui.QLabel):
    """Label for the distance from the center of the cameras"""
    
    def __init__(self, text):
        
        super(positionLabel, self).__init__(text)
        
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Maximum)
        sizePolicy.setHeightForWidth(True)
        self.setSizePolicy(sizePolicy)
       
    def sizeHint(self):

        return QtCore.QSize(100,100)

    def heightForWidth(self, width):

        return width 
        
        
class positionWidget(QtGui.QWidget):
    
    def __init__(self, minPos, maxPos, idealPos, error = 250):
        
        super(positionWidget, self).__init__()
        
        self.minPos = minPos
        self.maxPos = maxPos
        self.idealPos = idealPos
        self.error = error
        self.initUI()
        
    def initUI(self):
        
        self.setMinimumSize(1, 25)
        
        self.value = 1000
     
        
    def paintEvent(self, e):
      
        qp = QtGui.QPainter()
        qp.begin(self)
        self.drawWidget(qp)
        qp.end()
        
    def transform_pos(self, pos, min_pos, step):
        """Transform a value to a position on the display"""
        
        return (pos - min_pos) * step
        
    def drawWidget(self, qp):
      
#        font = QtGui.QFont('Serif', 7, QtGui.QFont.Light)
#        qp.setFont(font)

        size = self.size()
        w = size.width()
        h = size.height()
     
        length = self.maxPos - self.minPos
        step = w / length

        pos = self.transform_pos(self.value,self.minPos,step)
        
        
        
        
        pen = QtGui.QPen(QtGui.QColor(16, 159, 221), 5)
        qp.setPen(pen)        
        qp.setBrush(QtGui.QColor(52,50,52))
        qp.drawRect(0, 0, w, h)
        
        
        
#        pen = QtGui.QPen(QtGui.QColor(255,255,255), 10)
#        qp.setPen(pen)      
#        qp.setBrush(QtGui.QColor(255,255,255))
#        qp.drawRect(self.transform_pos(self.idealPos - self.error, self.minPos, step), 0, self.error * 2 * step, h)
        
        
        
        ##Draw the line
        if (self.idealPos - self.error) < self.value < (self.idealPos + self.error):
            
            pen = QtGui.QPen(QtGui.QColor(255,255,255), 8, QtCore.Qt.SolidLine)
        
        else:
            
            pen = QtGui.QPen(QtGui.QColor(255,255,255), 8, QtCore.Qt.SolidLine)
                
        qp.setPen(pen)
        qp.drawLine(pos, 1, pos, h)
        
        
    def setValue(self, value):
        """If the value has changed repaint the widget"""
        if value != self.value:
            
            self.value = value
            self.repaint() 
        
            
            
class virtualKeyboard(QtGui.QDialog):
    """"A virtual Keyboard"""
    
    def __init__(self, parent = None):
        
        super(virtualKeyboard, self).__init__(parent)    

        
        self.create_keys()
        
        
        
    def create_keys(self):
  
        self.lower_key_labels  =  [['1','2','3','4','5','6','7','8','9','0'],
                                   ['q','w','e','r','t','y','u','i','o','p'],
                                   ['a','s','d','f','g','h','j','k','l',''],
                                   ['CAP','z','x','c','v','b','n','m','<-',''],
                                   ['','Spacebar','']]       
        
        self.upper_key_labels  =  [['1','2','3','4','5','6','7','8','9','0'],
                                   ['Q','W','E','R','T','Y','U','I','O','P'],
                                   ['A','S','D','F','G','H','J','K','L',''],
                                   ['CAP','Z','X','C','V','B','N','M','<-',''],
                                   ['','Spacebar','']] 
        
        self.alt_key_labels  =  [['1','2','3','4','5','6','7','8','9','0'],
                                   ['@','£','&','_','(',')',':',';','"',''],
                                   ['','!','#','=','*','/','+','-','*',''],
                                   ['CAP',',','.','','','','','','<-',''],
                                   ['','Spacebar','']] 
                
        CAP_f = os.path.join(base_path, 'misc_files', 'shift_key.png')
        alt_f = os.path.join(base_path, 'misc_files', 'alt_keys.png')
        
        
        self.buttons = [[    {'lower': '1', 'upper': '1', 'alt': '1', 'type': 'text'},
                             {'lower': '2', 'upper': '2', 'alt': '2', 'type': 'text'},
                             {'lower': '3', 'upper': '3', 'alt': '3', 'type': 'text'},
                             {'lower': '4', 'upper': '4', 'alt': '4', 'type': 'text'},
                             {'lower': '5', 'upper': '5', 'alt': '5', 'type': 'text'},
                             {'lower': '6', 'upper': '6', 'alt': '6', 'type': 'text'},
                             {'lower': '7', 'upper': '7', 'alt': '7', 'type': 'text'},
                             {'lower': '8', 'upper': '8', 'alt': '8', 'type': 'text'},
                             {'lower': '9', 'upper': '9', 'alt': '9', 'type': 'text'},
                             {'lower': '0', 'upper': '0', 'alt': '0', 'type': 'text'}],

                            [{'lower': 'q', 'upper': 'Q', 'alt': '@', 'type': 'text'},
                             {'lower': 'w', 'upper': 'W', 'alt': '£', 'type': 'text'},
                             {'lower': 'e', 'upper': 'E', 'alt': '&', 'type': 'text'},
                             {'lower': 'r', 'upper': 'R', 'alt': '_', 'type': 'text'},
                             {'lower': 't', 'upper': 'T', 'alt': '(', 'type': 'text'},
                             {'lower': 'y', 'upper': 'Y', 'alt': ')', 'type': 'text'},
                             {'lower': 'u', 'upper': 'U', 'alt': ':', 'type': 'text'},
                             {'lower': 'i', 'upper': 'I', 'alt': ';', 'type': 'text'},
                             {'lower': 'o', 'upper': 'O', 'alt': '"', 'type': 'text'},
                             {'lower': 'p', 'upper': 'P', 'alt': '', 'type': 'text'}],

                            [{'lower': 'a', 'upper': 'A', 'alt': '', 'type': 'text'},
                             {'lower': 's', 'upper': 'S', 'alt': '!', 'type': 'text'},
                             {'lower': 'd', 'upper': 'D', 'alt': '#', 'type': 'text'},
                             {'lower': 'f', 'upper': 'F', 'alt': '=', 'type': 'text'},
                             {'lower': 'g', 'upper': 'G', 'alt': '*', 'type': 'text'},
                             {'lower': 'h', 'upper': 'H', 'alt': '/', 'type': 'text'},
                             {'lower': 'j', 'upper': 'J', 'alt': '\\', 'type': 'text'},
                             {'lower': 'k', 'upper': 'K', 'alt': '+', 'type': 'text'},
                             {'lower': 'l', 'upper': 'L', 'alt': '-', 'type': 'text'},
                             {'lower': '', 'upper': '', 'alt': '*', 'type': 'text'}],

                            [{'lower': CAP_f, 'upper': CAP_f, 'alt': CAP_f, 'type': 'icon', 'name': 'CAP'},
                             {'lower': 'z', 'upper': 'Z', 'alt': '.', 'type': 'text'},
                             {'lower': 'x', 'upper': 'X', 'alt': ',', 'type': 'text'},
                             {'lower': 'c', 'upper': 'C', 'alt': '', 'type': 'text'},
                             {'lower': 'v', 'upper': 'V', 'alt': '', 'type': 'text'},
                             {'lower': 'b', 'upper': 'B', 'alt': '', 'type': 'text'},
                             {'lower': 'n', 'upper': 'N', 'alt': '', 'type': 'text'},
                             {'lower': 'm', 'upper': 'M', 'alt': '', 'type': 'text'},
                             {'lower': '<-', 'upper': '<-', 'alt': '<-', 'type': 'text'},
                             {'lower': '', 'upper': '', 'alt': '', 'type': 'text'}],
                       
                            [{'lower': alt_f, 'upper': alt_f, 'alt': alt_f, 'type': 'icon', 'name': 'theta'},
                             {'lower': 'SPACEBAR', 'upper': 'SPACEBAR', 'alt': 'SPACEBAR','type': 'text'},
                             {'lower': '', 'upper': '', 'alt': '', 'type': 'text'}]]
              
        self.button_case = 'upper' #Start the buttons in lower case. Used to toggle the case   
        self.alt_keys = False #Start not on alt keys
                      
#        self.key_buttons = [[Text_Button(k) for k in row] for row in self.lower_key_labels] #Create all the buttons

        
       
        for row in self.buttons:
            for k in row:
                
                if k['type'] == 'text':
                    k['button'] = Text_Button(k[self.button_case])
                elif k['type'] == 'icon':
                    k['button'] = Icon_Button(k[self.button_case])
            
        self.connect_to_misc_buttons() ##Connect the shift and alt key
                      
        master_grid = QtGui.QGridLayout() #Master layout
        
        row_grids = [QtGui.QGridLayout() for r in range(len(self.buttons))] #Row Layouts
    
        
        ##Layout each row
        
        for key in range(len(self.buttons[0])):
            row_grids[0].addWidget(self.buttons[0][key]['button'], 0, key) #Add the first row of buttons to the first grid
            
        for key in range(len(self.buttons[1])):
            row_grids[1].addWidget(self.buttons[1][key]['button'], 0, key) #Add the second row of buttons to the first grid
        
        for key in range(len(self.buttons[2])):
            row_grids[2].addWidget(self.buttons[2][key]['button'], 0, key) #Add the third row of buttons to the first grid
         
        for key in range(len(self.buttons[3])):
            row_grids[3].addWidget(self.buttons[3][key]['button'], 0, key) #Add the forth row of buttons to the first grid
            
        #Add Spacebar    
        row_grids[4].addWidget(self.buttons[4][0]['button'], 0, 0, 1,3)
        row_grids[4].addWidget(self.buttons[4][1]['button'], 0, 3, 1,5)
        row_grids[4].addWidget(self.buttons[4][2]['button'], 0, 8, 1,4)

        
        #Add all to the master grid
        master_grid.addLayout(row_grids[0], 0, 0)
        master_grid.addLayout(row_grids[1], 1, 0)
        master_grid.addLayout(row_grids[2], 2, 0)
        master_grid.addLayout(row_grids[3], 3, 0)
        master_grid.addLayout(row_grids[4], 4, 0)
        
        self.setLayout(master_grid)           
     
#        self.set_case('lower')
       
#        self.setStyleSheet("background-color: rgba(0, 0, 0, 100%);")
        
        
        
#        self.hide() #Make the keyboard invisible
    
    def connect_to_buttons(self, obj):
        """connect all the buttons to a suitable Qt object"""
        
        for row in self.buttons:
            for k in row:
                if k['type'] == 'text':
                    k['button'].pressed.connect(obj)
    
    
    def connect_to_misc_buttons(self):
        """connect the keyboard to the shiftkey"""
        for row in self.buttons:
            for k in row:
                if (k['type'] == 'icon') and (k['name'] == 'CAP'):
                    k['button'].pressed.connect(self.set_case)
                
                if (k['type'] == 'icon') and (k['name'] == 'theta'):
                    k['button'].pressed.connect(self.set_alt_keys)
    
    
    @Slot()
    def set_alt_keys(self):
        
        print("RECEIVED SIGNAL ALT")
        if not self.alt_keys:
            print("HI")
            self.alt_keys = True
            
            for row in self.buttons:
                for k in row:
                    if  k['type'] == 'text':
                        k['button'].change_text(k['alt'])
        
        else:
            #When changing back to text change back to whatever the button case was previously
            self.alt_keys = False
                
            for row in self.buttons:
                for k in row:
                    if  k['type'] == 'text':
                        k['button'].change_text(k[self.button_case])
                
    @Slot()            
    def set_case(self):
        """Toggle the letter case"""
      
        
        print("RECIEVED SIGNAL")
        
        if self.button_case == 'lower':
            
            self.button_case = 'upper'            
            
            for row in self.buttons:
                for k in row:
                    if  k['type'] == 'text':
                        k['button'].change_text(k['upper'])
                    
        elif self.button_case == 'upper':
            
            self.button_case = 'lower'
            for row in self.buttons:
                for k in row:                
                    if k['type'] == 'text':
                        
                        k['button'].change_text(k['lower'])
                        
          
    @Slot(int)
    def cap_zero_len(self, text_len):
        
        print("RECIEVED LENGTH: {}".format(text_len))
        
        if text_len == 0:
            
            if self.button_case == 'lower':
                self.button_case = 'upper'            
                
                for row in self.buttons:
                    for k in row:
                        if  k['type'] == 'text':
                            k['button'].change_text(k['upper'])
        
        elif text_len == 1:
            if self.button_case == 'upper':
                self.button_case = 'lower'            
                
                for row in self.buttons:
                    for k in row:
                        if  k['type'] == 'text':
                            k['button'].change_text(k['lower'])
   
        
class Icon_Button(QtGui.QToolButton):
    """A Icon button class for the virtual keyboard"""
    
    pressed = Signal()

    def __init__(self, icon_f, parent=None):
        """Pass the file location of the icon"""
        super(Icon_Button, self).__init__(parent)

        self.icon_f = icon_f 
        self.setSizePolicy(QtGui.QSizePolicy.Expanding,
                QtGui.QSizePolicy.Preferred)
                
        rMyIcon = QtGui.QPixmap(self.icon_f);
        self.setIcon(QtGui.QIcon(rMyIcon))          
                
        self.setStyleSheet("""background-color: rgb(52,50,52); color: rgb(255,255,255); border: 1px solid rgb(34, 85, 96); 
                                     border-radius: 0px; font-family: embrima; font-size: 17px; font-weight: 700 """)


    def sizeHint(self):
        size = super(Icon_Button, self).sizeHint()
        size.setHeight(size.height() + 20)
        size.setWidth(max(size.width(), size.height()))
        return size
      
    def mousePressEvent(self, e):
        

       self.pressed.emit()   

                
       self.setStyleSheet("""background-color: rgb(255, 105, 0); 
                            border: 0px;
                            color: rgb(255,255,255);""")
            
            
    def mouseReleaseEvent(self, e):
   
       if self.text != '':
            self.setStyleSheet("""background-color: rgb(52,50,52); color: rgb(255,255,255); border: 1px solid rgb(34, 85, 96); 
                                     border-radius: 0px; font-family: embrima; font-size: 17px; font-weight: 700 """)


                                        
           
    
class Text_Button(QtGui.QToolButton):
    """A text button class for the keyboard"""
    
    pressed = Signal(str)

    def __init__(self, text, parent=None):
        super(Text_Button, self).__init__(parent)

        self.text = text
        self.setSizePolicy(QtGui.QSizePolicy.Expanding,
                QtGui.QSizePolicy.Preferred)
        self.setText(text)
        
        
        
        self.setStyleSheet("""background-color: rgb(52,50,52); color: rgb(255,255,255); border: 1px solid rgb(34, 85, 96); 
                                     border-radius: 0px; font-family: embrima; font-size: 17px; font-weight: 700 """)

    def sizeHint(self):
        size = super(Text_Button, self).sizeHint()
        size.setHeight(size.height() + 20)
        size.setWidth(max(size.width(), size.height()))
        return size
      
    def mousePressEvent(self, e):
        
        if self.text != '':
       
            self.pressed.emit(self.text)  
            print("Key: {}".format(self.text))
            
                
            self.setStyleSheet("""background-color: rgb(255,105,0);                         
                                        color: rgb(255,255,255);
                                        font-weight: 800""")
                                                        
    def mouseReleaseEvent(self, e):
     
        if self.text != '':
            self.setStyleSheet("""background-color: rgb(52,50,52); color: rgb(255,255,255); border: 1px solid rgb(34, 85, 96); 
                                     border-radius: 0px; font-family: embrima; font-size: 17px; font-weight: 700 """)
    def change_text(self, text):
        self.text = text
        self.setText(text)
           

        
       
class MyTimeLineEdit(QtGui.QLineEdit):
    """Widget for entering the recording time"""
 
    pressed = Signal() #Signal to emit when mousepress focused    
    end_focus = Signal()    
    text_length = Signal(int) #A integer showing how long the text is
    
    def __init__(self, parent = None):
        super(MyTimeLineEdit, self).__init__(parent)
        self.setObjectName("MyTimeLineEdit")
        self.text2 = ''
        
        self.in_focus = None
       
        self.enabled = True
        
    def mousePressEvent(self, e):
        
        self.pressed.emit() #Emit a signal when the key is pressed
        print("Key Pressed")
    
    def focusInEvent(self, e):
        
        QtGui.QLineEdit.focusInEvent(self, QtGui.QFocusEvent(QtCore.QEvent.FocusIn)) #Call the default In focus event
        self.text_length.emit(len(self.text2))
        self.in_focus = True
        
        print("IN")
    
    def focusOutEvent(self, e):
        
        QtGui.QLineEdit.focusOutEvent(self, QtGui.QFocusEvent(QtCore.QEvent.FocusOut)) #Call the default Outfocus event
           
        self.in_focus = False
        self.end_focus.emit() #Emit signal that focus was lost
        print("OUT")
        
    @Slot(str)    
    def recieve_input(self, inp):

        if self.in_focus and self.enabled:        
        
            print("Recieved key {}".format(inp))
            
            
                
            if inp == '<-':
                
                self.text2 = self.text2[:-1]
    
            elif inp =='SPACEBAR':
                
                self.text2 += ''
                
            else:      
                
                if self.test_int(inp):
                    
                    self.text2 += inp
                
                
            self.setText(self.text2)           
            
            self.text_length.emit(len(self.text2))
            
    def test_int(self, text_):
        """Test whether a string can be cast to an integer"""
        
        is_int = True
            
        try:  
            
            int(text_)      
            
        except ValueError: 
            
            is_int = False
        
        if not is_int:
            
            print("Not a valid integer")
            
            return False
        
        else:
            
            return True
            
    def toggle_enable(self):
        
        if self.enabled:
            self.enabled = False
        else:
            self.enabled = True
            
    def reset_text(self):
        
        self.text2 = ''
        self.setText('')
        self.text_length.emit(len(self.text2)) 
            
    def set_text(self, text_):
        """Override the text"""
        self.text2 = text_
        self.setText(text_)
        self.text_length.emit(len(self.text2))
        
    def value(self):
        """Only for use with the Record time edit
        Return the value entered into the record time as an int"""
        
        try:
            value = int(self.text())
        except ValueError as e:
            print("{}: The record value is not a valid integer".format(e))
        
        return value
 

      
class MyLineEdit(QtGui.QLineEdit):
    """A line edit that can take input from the virtual keyboard"""
 
    pressed = Signal() #Signal to emit when mousepress focused    
    end_focus = Signal()    
    text_length = Signal(int) #A integer showing how long the text is
    
    def __init__(self, parent = None):
        super(MyLineEdit, self).__init__(parent)
        
        self.text2 = ''
        
        self.in_focus = None
        
        self.enabled = True
       
    def mousePressEvent(self, e):
        
        self.pressed.emit() #Emit a signal when the key is pressed
        print("Key Pressed")
    
    def focusInEvent(self, e):
        
        QtGui.QLineEdit.focusInEvent(self, QtGui.QFocusEvent(QtCore.QEvent.FocusIn)) #Call the default In focus event
        self.text_length.emit(len(self.text2))
        self.in_focus = True
        
        print("IN")
    
    def focusOutEvent(self, e):
        
        QtGui.QLineEdit.focusOutEvent(self, QtGui.QFocusEvent(QtCore.QEvent.FocusOut)) #Call the default Outfocus event
           
        self.in_focus = False
        self.end_focus.emit() #Emit signal that focus was lost
        print("OUT")
        
    @Slot(str)    
    def recieve_input(self, inp):

        if self.in_focus and self.enabled:        
        
            print("Recieved key {}".format(inp))
            
            if inp =='SPACEBAR':
                self.text2 += ' '
            elif inp == '<-':
                self.text2 = self.text2[:-1]
            else:
                self.text2 += inp
                
                
            self.setText(self.text2)           
            
            self.text_length.emit(len(self.text2))
            

    def toggle_enable(self):
        
        if self.enabled:
            self.enabled = False
        else:
            self.enabled = True
            
    def reset_text(self):
        
        self.text2 = ''
        self.setText('')
        self.text_length.emit(len(self.text2)) 
            
    def set_text(self, text):
        """Override the text"""
        self.text2 = text
        self.setText(text)
        self.text_length.emit(len(self.text2))
        
    def value(self):
        """Only for use with the Record time edit
        Return the value entered into the record time as an int"""
        
        try:
            value = int(self.text2)
        except ValueError as e:
            print("{}: The record value is not a valid integer".format(e))
        
        return value
    
    def currentText(self):
        """Get the current text. Does exactly the same as self.text(). Implimented to make consistent with other widgets"""
      
        return self.text()
        
        

class MyDateEdit(QtGui.QDateEdit):
    """
    DEPRECIATED: Now replaced by a special pop up widget
    A child of the QDateEdit that emits a signal when it is pressed"""
 
    pressed = Signal() #Signal to emit when mousepress focused    
    end_focus = Signal()    
    
    def __init__(self, parent = None):
        super(MyDateEdit, self).__init__(parent)
        
        self.text = ''
        
        self.in_focus = None
       
        self.setCalendarPopup(True)
        self.calendar = self.calendarWidget()
        
        self.setDate(QtCore.QDate(2000, 1, 1))
        
#    def mousePressEvent(self, e):
#        
#        self.pressed.emit() #Emit a signal when the key is pressed
#        print("Key Pressed")
    
    def focusInEvent(self, e):
        
        QtGui.QDateEdit.focusInEvent(self, QtGui.QFocusEvent(QtCore.QEvent.FocusIn)) #Call the default In focus event
        
        self.in_focus = True
        
        print("IN")
    
    def focusOutEvent(self, e):
        
        QtGui.QDateEdit.focusOutEvent(self, QtGui.QFocusEvent(QtCore.QEvent.FocusOut)) #Call the default Outfocus event
           
        self.in_focus = False
        self.end_focus.emit() #Emit signal that focus was lost
        print("OUT")
        
    @Slot(str)    
    def recieve_input(self, inp):

        if self.in_focus:        
            
             
            self.text = self.sectionText(self.currentSection())
            print(self.text, self.currentSection())
            print(self.date())
            
            
    def reset_date(self):
        
        self.setDate(QtCore.QDate(2000, 1, 1))
   
        
        
class Console(QtGui.QTextEdit):
    """A PSAT console for the data analysis GUI"""
    def __init__(self, parent  = None):
        
        super(Console, self).__init__(parent)        
        
        self.promt_welcome()
            
    
    def addText(self, text):
        
        if self.toPlainText() == '':
            
            self.setText(text)
        
        else:
            
            self.setText(self.toPlainText() + '\n' + text)
        
        QtGui.QApplication.processEvents() 
        
    def newLine(self):
        
        self.setText(self.toPlainText() + '\n')
        QtGui.QApplication.processEvents() 
    
    def clearConsole(self):
        """Wipe all text from the console"""
        
        self.setText("")
        
    def promt_welcome(self):
        
        self.addText("Welcome to the PSAT data analysis tool\n\nSet the location of the PSAT data you wish to analyse using the `Data Control' menu to begin...")
        self.newLine()
    
    @Slot()    
    def promt_select_data(self):
        self.clearConsole()
        self.addText("Select the data you wish to process from the list in the left panel...\n\nThen press Process...")
        self.newLine()
    
    def promt_process_data(self, n_records):
        self.clearConsole()
        self.addText("You have selected {} records to process:".format(n_records))
        self.newLine()
        
        
class QLED(QtGui.QWidget):
    """Not currently used or doing anything. Probably doesn't work"""
    def __init__(self, parent = None):   
        super(QLED, self).__init__(parent)
        
        palette = QtCore.QPalette(self.palette())
        palette.setColor(palette.Background, QtCore.Qt.transparent)
        self.setPalette(palette)
        
        
class feedbackDialog(QtGui.QDialog):

    def __init__(self, parent = None, PL = -999):       
        
        super(feedbackDialog, self).__init__(parent) 
        self.setWindowTitle("Results")
        
        self.PL = PL #The participants PL
        
        self.get_PL_as_percentile()
        
        self.init_layout()
        
    def init_layout(self):
        
        self.myLayout = QtGui.QVBoxLayout()
        self.add_PL_label() #Add the label
        self.add_percentile_label()
        self.add_figure()
        self.add_closeButton()
        
        self.setLayout(self.myLayout)
        
    def get_PL_as_percentile(self):
        """Assuming a normal distribution return the percentile of the score"""
        
        self.mean = 250
        self.std = 50
        
        self.PL_percent = sts.norm.cdf(self.PL, self.mean, self.std) 
        
    def add_PL_label(self):
   
        PL_label = QtGui.QLabel("Path Length = {:.0f}mm".format(self.PL))      
        PL_label.setAlignment(QtCore.Qt.AlignCenter)
        self.myLayout.addWidget(PL_label)
        
    def add_percentile_label(self):
        

        pc_label = QtGui.QLabel("Percentile = {0:.0f}%".format(self.PL_percent*100))   
        pc_label.setAlignment(QtCore.Qt.AlignCenter)
        
        self.myLayout.addWidget(pc_label)
        
    def add_figure(self):
        
        fig = plt.figure(figsize = (2.5,1.75), facecolor=(52/255,50/255,52/255),edgecolor='white')
        ax1 = fig.add_subplot(111, axisbg='none')
        ax1.get_xaxis().set_visible(False)
        ax1.get_yaxis().set_visible(False)      
   
        x = np.linspace(-5, 5, 1000)
        y = sts.norm.pdf(x, 0, 1)        
        
        ax1.plot(x, y, color = (16/255, 159/255, 221/255))
        ax1.axvline((self.PL - self.mean) /self.std , color = (221/255, 89/255, 2/255))

        plt.tight_layout()

        self.canvas = FigureCanvas(fig)

        self.myLayout.addWidget(self.canvas)
        
    def add_closeButton(self):
        
        self.closeButton = QtGui.QPushButton("Ok", parent = self)
        self.closeButton.clicked.connect(self.close)
        
        self.myLayout.addWidget(self.closeButton)
        
     
