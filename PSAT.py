# -*- coding: utf-8 -*-
"""
Postural Sway Assesment Tool GUI.

"""

import sys
import os


if getattr(sys, 'frozen', False):
   base_path = sys._MEIPASS   
else:   
   base_path = os.path.dirname(os.path.realpath(sys.argv[0]))   

sys.stderr = open(os.path.join(base_path, 'stderr_log.txt'), 'w')
sys.stdout = open(os.path.join(base_path, 'stdout.txt'), 'w')


print("The basepath is {}".format(base_path))
print(getattr(sys, 'frozen', False))
print(os.path.dirname(sys.argv[0]))
print(os.path.dirname(os.path.realpath(sys.argv[0])))

try:
   from PySide import QtGui, QtCore
   Signal = QtCore.Signal
   Slot = QtCore.Slot
    
#   from PyQt4 import QtCore, QtGui  #Note that some code will need to be changed if this is used (Signal has different call signiture)
#   Signal = QtCore.pyqtSignal
#   Slot = QtCore.pyqtSlot
   import matplotlib
   matplotlib.use("Qt4Agg")
   matplotlib.rcParams['backend.qt4'] = 'PySide'
   onDesktop = False
    
except ImportError as exp:
    print(exp)
    print("Looking for PyQT")

    from PyQt4 import QtCore, QtGui  #Note that some code will need to be changed if this is used (Signal has different call signiture)
    Signal = QtCore.pyqtSignal
    Slot = QtCore.pyqtSlot
    
    onDesktop = True

debug = False


import cv2
import threading, time, pdb, multiprocessing, glob, subprocess #Imports from standard library
import ctypes #To fix garbage collection bug
import pandas as pd
import numpy as np
import matplotlib.pylab as plt
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
import seaborn as sns

import posturalCam_master_NETWORK as backend
from file_system import FileOrderingSystem
from shh_client import shh_client
import ir_marker

from PSAT_widgets import * #Import all the custom widgets for PSAT


   

   

#import posturalCam_master_NETWORK as pCam
def vector_magnitude(v):
    """Calculate the magnitude of a vector"""
    
    #Check that v is a vector
    if v.ndim != 1:
        raise TypeError("Input is not a vector")
    return np.sqrt(np.sum(np.square(v)))  
    
def load_demo_images():
    """For demo purposes we can load 2 images"""
    frame1 = cv2.imread(os.path.join(base_path, 'misc_files', 'cam_im1.png'))
    frame2 = cv2.imread(os.path.join(base_path, 'misc_files', 'cam_im1.png'))
    
    return frame1, frame2       
        
##---------------------------------------------##
##---------------------------------------------##       
##---------------The Main GUI------------------##        
##---------------------------------------------##        
##---------------------------------------------##        
##---------------------------------------------##
##---------------------------------------------##     


   
class MainWindow(QtGui.QMainWindow):
    """
    The main PSAT GUI    
    """
    camerasConnected = Signal() #A QT signal to indicate that the camera backend is live
    data_dir_set = Signal() #A Qt signal to indicate that the data directory has been set
    record_item_clicked = Signal(str)
    
    def __init__(self):
        """Initialise the PSAT GUI"""
        
        super(MainWindow, self).__init__(None)  
        
        self.participant_list_loaded = False
        self.storage_loc = '' #The storage location for the recorded data
        
        self.initUI() #Set up the main GUI             
        
    def initUI(self):
        """Setup the main window size, title and layout. Create all the widgets"""
        self.setGeometry(50, 50, 800, 480) #Set the GUI size
        
        
        self.setFixedSize(800, 480) #Do not allow the window to resize on RPi
            
        self.setWindowTitle('Postural Sway Assessment Tool') #Set the GUI title          
        QtGui.QApplication.setStyle(QtGui.QStyleFactory.create('Cleanlooks')) #Set the GUI look style
        
        self.timer = QtCore.QTimer() #A timer for controlling the scrolling text at the top right of the GUI   
        
        self.create_widgets()                     
        self.add_menubar() #Add a menubar to the GUI       
        self.show() #Display the GUI
           
        
        
        onDesktop = False #Just a work around, but the onDesktop variable should be depreciated in future. The app functions differently on the RPi and on windows
        if not onDesktop:
            
            self.camera_backend_live = False #Marker that backend has been imported
            self.create_camera_backend()
        
        
        
    def add_menubar(self):
        """Add a menubar to the main UI. This controls all the buttons in the menubar"""
        
        ##drop down menu
        exitAction = QtGui.QAction(QtGui.QIcon('exit.png'), '&Shutdown', self) 
        exitAction.setStatusTip('Shutdown PSAT')
        exitAction.triggered.connect(self.shutdown_event)
        
        #New participant button
        new_partMenu = QtGui.QAction(QtGui.QIcon('exit.png'), '&New Participant', self)        
        new_partMenu.triggered.connect(self.new_participant)
        
        
        #Choose storage location        
        data_locMenu = QtGui.QAction(QtGui.QIcon('exit.png'), '&Set Save Directory', self)   
        data_locMenu.triggered.connect(self.get_storage_location)
         
        
        #Load a participant list
        self.part_listMenu = QtGui.QAction(QtGui.QIcon(''), '&Load Participant List', self)
        self.part_listMenu.triggered.connect(self.toggle_load_part_button)
        
        #Select different windows
        
        self.processDataMenu = QtGui.QAction(QtGui.QIcon(''), '&Process Data', self)
        self.processDataMenu.triggered.connect(self.processing_window)

        #Add the menubar and the menu buttons
        menubar = self.menuBar()   
        
#        menubar.setFixedHeight(25)
        fileMenu = menubar.addMenu('&File')        
        fileMenu.addAction(exitAction)          
        
        participantMenu = menubar.addMenu('&Data Control')         
        participantMenu.addAction(data_locMenu)
        participantMenu.addAction(self.part_listMenu)
        participantMenu.addAction(new_partMenu)
        
        processMenu = menubar.addMenu("&Data Processing")
        processMenu.addAction(self.processDataMenu)
          
        self.rec_scroll = recordingLocLabel(2.3) #Takes the speed as an input 
        
        menubar.setCornerWidget(self.rec_scroll, QtCore.Qt.TopRightCorner)
        
#        menubar.setCornerWidget(test_lab, QtCore.Qt.TopRightCorner)
        
        self.timer.timeout.connect(self.rec_scroll.scrollText)
        self.timer.start(33)
        
    def create_widgets(self):
        """Add all the widgets to the GUI"""
        
        self.central_widget = QtGui.QWidget() #The main widget
        
        self.central_widget.setContentsMargins(10,0,2,5) #Set the margins of the main window
        
        grid = QtGui.QGridLayout() #Add a grid layout
        grid.setSpacing(15)                

        #Create and add the different displays (demographics; camera; and processing)
        grid.addWidget(self.create_demographics_group(), 0,0, 3,1)
        grid.addWidget(self.create_camera_group(), 0,0, 1,1)
#        grid.addWidget(self.create_recording_group(), 0, 0, 1, 1)
        grid.addWidget(self.create_processing_group(), 0, 0, 1, 1)
  
    

#        grid.addWidget(self.create_keyboard(), 3, 0, 4, 1) 
        
        
        if onDesktop:
#            self.show_window_1() 
            self.show_window_3() 
            
#            
#            self.show_window_2()
        else:
            
            self.show_window_1()      
        
        #Set as the main widget
        self.central_widget.setLayout(grid) 
        self.setCentralWidget(self.central_widget)
        
        
    def create_camera_backend(self):
        """Import the camera backend and establist a connection with the server. Calls self.start_camera_backend_connection() in a thread
           Also opens a dialog box which disappeard when a connection is made. Or you can click cancel and stop the connection - by calling self.stop_connection
        
        This only works on PSAT (Not on desktop)"""
        
        self.attempt_connection = True        
        
        self.startDialog = cameraSystemDialog(self) #Open a dialog box to ask whether to cancel establishing the connection
        self.startDialog.CloseButton.clicked.connect(self.stop_attempt_connection) #IF closed clicked on the startDialog stop the thread
        self.camerasConnected.connect(self.startDialog.camerasLive) #When a connection is made this closes the dialog
        
        threading.Thread(target = self.start_camera_backend_connection).start() #Start a thread which will attempt to connect to the server

        #self.camera_backend_live = self.backend_camera.TCP_client_start() #If it connects set the backend_live = True
        
#        self.camera_backend_live = True #Signal that the backend has been imported
        
      
    def start_camera_backend_connection(self):
        """Try to establish a connection to the server RPi"""
        self.backend_camera = backend.posturalCam()
        
        self.camera_backend_live = False
        
        while self.attempt_connection:
            print("LOOKING FOR CONNECTION")
            self.camera_backend_live = self.backend_camera.TCP_client_start() 
                    
            if self.camera_backend_live:
                print("BACKEND LIVE")
                self.camerasConnected.emit()
                self.stop_attempt_connection()
            else:
                print("BACKEND NOT LIVE")
                
        print("NO LONGER LOOKING")
        
    def stop_attempt_connection(self):
        
        self.attempt_connection = False   
    
        
    def processing_window(self):
        """Menubar function:
        Navigate the processing window if a storage location has been set"""
        
        self.show_window_3()
        
#        if not self.storage_loc == '':
#            
#            self.show_window_3()
#            
#        else:
#            
#            error_msgBox = QtGui.QMessageBox(self)
#            error_msgBox.setText("""A storage location has not been set.\n\nSelect a storage location by clicking Data Control -> Set Save Directory""" )
#            error_msgBox.exec_()
#            return
                    
        
    def get_storage_location(self):
        """Menubar function:
        Open a dialog to select the folder to which you would like to save PSAT data to"""
        
        if onDesktop:
            self.storage_loc = QtGui.QFileDialog.getExistingDirectory(self, 'Open file', 
                '/media/pi/')
        else:            
            self.storage_loc = QtGui.QFileDialog.getExistingDirectory(self, 'Open file', 
                    '/media/pi/')        
        
        
        self.rec_scroll.setMessage(self.storage_loc)    
        
        if self.window_live == 3:
            self.data_dir_set.emit() #Emit a Qt signal if the storage location is set when in data processing mode
                
        
    def shutdown_event(self):
        """Menubar function:
        Shut down the RPi's or exit to the desktop. This does the following:
                1) Opens a dialog box asking if the user would like to shut down the RPi
                2) If shutdown is requested it will first tell the RPi Server to close. Then it makes a SSH connection to the server pi and tells it to shutdown
                3) Then quits the PSAT application and shuts down the client RPi
        """
        
        shutdown_msg = "Power down PSAT?"        
        reply = QtGui.QMessageBox.question(self, "Shutdown", shutdown_msg, QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)        
        
        
        if reply == QtGui.QMessageBox.Yes:         
            
            if self.camera_backend_live:
                self.backend_camera.TCP_client_shutdown_server() #Ask the server to shutdown. Closes the server but doesnt close the Raspberry Pi

                self.shh_connection = shh_client() #Make a connection to the client
                #self.shh_connection_thread.join() #Wait till the server has shutdown
                self.shh_connection.shutdown_server_pi() #Shutdown the server pi. Shuts down the server raspberry pi
                subprocess.call(["sudo", "shutdown", "now"]) #Shutdown the client pi

            QtCore.QCoreApplication.instance().quit() #Quit Application. This will close down the RPis in future
        else:
            print("Not closing")
    
            
        close_msg = 'Exit to Desktop?'
        reply2 = QtGui.QMessageBox.question(self, "Shutdown", close_msg, QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
        
        if reply2 == QtGui.QMessageBox.Yes:
            QtCore.QCoreApplication.instance().quit() #Quit Application. 



    ##---------------------------------------------##
	##---------------------------------------------##       
	##------------PSAT GUI LAYOUT METHODS----------##        
	##---------------------------------------------##        
	##---------------------------------------------##        
	##---------------------------------------------##
	##---------------------------------------------##


    def create_demographics_group(self):
        """Create the demographics window. Controls the layout and creates all the necessary widgets"""
        #Main Groupings
        
        self.demographics_container = QtGui.QWidget()       
        self.demographicsBox = QtGui.QGroupBox("Demographics")   
        self.optionsBox = QtGui.QGroupBox("Options")   
        
        
        VBox = QtGui.QVBoxLayout()
        
        HBox = QtGui.QHBoxLayout()
        HBox.setSpacing(20)
#        HBox.setMargin(0)
        HBox.addWidget(self.demographicsBox)
        HBox.addWidget(self.optionsBox)
        
        VBox.addLayout(HBox)
       
        self.demographics_container.setLayout(VBox)
        
        
        #Labels and buttons        
#        rec_loc_label = QtGui.QLabel('Recording Loc')   
#        self.rec_loc_ = QtGui.QLabel('')
        
        Forename_label = QtGui.QLabel('Forename:')     
        self.Forename_edit = MyLineEdit(self)
#        self.Forename_edit.pressed.connect(self.show_keyboard)    
#        self.Forename_edit.end_focus.connect(self.hide_keyboard)  
        
        Surname_label = QtGui.QLabel('Surname:')
        self.Surname_edit = MyLineEdit(self)
#        self.Surname_edit.pressed.connect(self.show_keyboard)    
#        self.Surname_edit.end_focus.connect(self.hide_keyboard)  
        
        Gender = QtGui.QLabel('Gender:')
        self.Gender_edit = QtGui.QComboBox()
        self.Gender_edit.addItem("Male")
        self.Gender_edit.addItem("Female")    
        
        ID = QtGui.QLabel("ID")
        self.ID_edit = MyLineEdit(self)
        
        Condition = QtGui.QLabel("Condition:")        
        
        self.ConditionStack = QtGui.QStackedWidget (self)
        self.Condition_edit = QtGui.QComboBox()
        self.Condition_edit.currentIndexChanged.connect(self.change_condition)
        self.Condition_edit.setStyleSheet("border-color: rgb(221, 89, 2)")
        
        self.Condition_edit_line = MyLineEdit(self)
        self.Condition_edit_line.setStyleSheet("border-color: rgb(221, 89, 2)")
        self.ConditionStack.addWidget (self.Condition_edit)
        self.ConditionStack.addWidget (self.Condition_edit_line)
        self.ConditionStack.setCurrentIndex(1)

        
#        self.ID_edit.pressed.connect(self.show_keyboard)    
#        self.ID_edit.end_focus.connect(self.hide_keyboard)
                
#        d.show()
#        self.d = myDateDialog()
        DOB = QtGui.QLabel('DOB:')
        self.DOB_edit = myDateLineEdit()
        self.DOB_edit.clicked.connect(self.getDOB)

        
        Record_Time_label = QtGui.QLabel("Time (Seconds):")
#        self.Record_Time = QtGui.QDoubleSpinBox()
#        self.Record_Time.setMinimum(0)
#        self.Record_Time.setValue(10)
        self.Record_Time = MyTimeLineEdit(self)
        self.Record_Time.set_text("30")
        
#        self.load_IDs = QtGui.QPushButton("Load Part List")
#        self.load_IDs.setFixedSize(150,35)
##        self.load_IDs.clicked.connect(self.load_file)
#        self.load_IDs.clicked.connect(self.toggle_load_part_button)
        
        check_ID = QtGui.QPushButton("Verify")
#        check_ID.setFixedSize(5,30)
        check_ID.setStyleSheet("background-color: rgb(16, 159, 221)")
        check_ID.clicked.connect(self.find_participant)
        
        start_Rec = QtGui.QPushButton("Next")
#        start_Rec.setFixedSize(5,30)
        start_Rec.clicked.connect(self.show_window_2)
               
        demographics_grid = QtGui.QGridLayout()      
        demographics_grid.setSpacing(15)
        
        demographics_grid.setContentsMargins(10, 25, 10, 10)
        
#        demographics_grid.addWidget(rec_loc_label, 0, 0, 1, 1)
##        demographics_grid.addWidget(self.rec_loc_, 0, 1, 1, 1)
        
        demographics_grid.addWidget(Forename_label, 0,0, 1,1)
        demographics_grid.addWidget(self.Forename_edit, 0, 1, 1, 1)
        
        demographics_grid.addWidget(Surname_label, 1, 0, 1, 1)
        demographics_grid.addWidget(self.Surname_edit, 1, 1, 1, 1)
        
        demographics_grid.addWidget(ID, 2, 0, 1, 1)
        demographics_grid.addWidget(self.ID_edit, 2, 1, 1, 1)
        
        demographics_grid.addWidget(Gender, 0, 2, 1, 1)
        demographics_grid.addWidget(self.Gender_edit, 0, 3, 1, 1)
        
        demographics_grid.addWidget(DOB, 1, 2, 1, 1)
        demographics_grid.addWidget(self.DOB_edit, 1, 3, 1, 1)
        
        demographics_grid.addWidget(check_ID, 2, 3, 1, 1)#
        
#        demographics_grid.addWidget(rec_loc_label, 3,0, 1, 1)
        
        self.demographicsBox.setLayout(demographics_grid)
        
        
        
        options_grid = QtGui.QGridLayout()
        options_grid.setSpacing(15)
        options_grid.setContentsMargins(10, 25, 10, 10)
        
        options_grid.addWidget(Record_Time_label, 0, 0, 1, 1)
        options_grid.addWidget(self.Record_Time, 0, 1, 1, 1)
        options_grid.addWidget(Condition, 1, 0, 1, 1)
        options_grid.addWidget(self.ConditionStack, 1, 1, 1, 1)  
        options_grid.addWidget(start_Rec, 2, 1, 1, 1)
        
        self.optionsBox.setLayout(options_grid)
#        
#        demographics_grid.addWidget(self.load_IDs, 3, 0, 1, 1)
        
#        
#        demographics_grid.addWidget(Condition, 3, 2, 1, 1)
#        demographics_grid.addWidget(self.Condition_edit, 3, 3, 1, 1)
#        
#        demographics_grid.addWidget(start_Rec, 3, 5, 1, 1)
##        #demographics_grid.addWidget(New_participant, 3, 5, 1, 1)
        
        VBox.addSpacing(5)
        self.create_keyboard()
        VBox.addWidget(self.keyboard)
#        VBox.setMargin(0)
        VBox.setContentsMargins(0,0,0,0)
        
        return self.demographics_container



    def create_camera_group(self):
        """Create the camera_preview window. Controls the layout and creates all the necessary widgets"""
        self.camera_container = QtGui.QWidget() #Container for all widgets
        self.camera_container.setObjectName("cameraContainer")
        self.camera_container.setContentsMargins(0,0,0,0)
     
        container_grid = QtGui.QVBoxLayout()      
        container_grid.setContentsMargins(0,0,0,0)
#        container_grid.setMargin(0)   
                  
        
        #Create a group box for each pane
        camera_box = QtGui.QGroupBox("Camera Preview") 
        triangulation_box = QtGui.QGroupBox("Triangulation")
        control_box = QtGui.QGroupBox("Control") 
        
        camera_box.setSizePolicy(QtGui.QSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.MinimumExpanding))
                
        self.camera_container.setLayout(container_grid)
        
     
        #Control Pane
        control_layout_spacer = QtGui.QVBoxLayout()
        control_layout_spacer.addSpacing(10)
        
        control_layout = QtGui.QHBoxLayout()   
        control_layout_spacer.addLayout(control_layout)
#        control_layout.setMargin(15)
        
        checkbox_container = QtGui.QWidget() 
        
        
     
        checkbox_container.setObjectName("camera_checkbox")        
#        checkbox_container.setStyleSheet(".QWidget {border: 1px solid rgb(221,89,2)}; ")
        checkbox_VLayout = QtGui.QVBoxLayout()
        
        self.preview_options_triangulate = QtGui.QCheckBox("Triangulate")
        self.preview_options_triangulate.setChecked(False)        
        self.record_options_send_video = QtGui.QCheckBox("Send Video")       
        self.record_options_send_video.setChecked(True)        
        self.record_options_send_video.setEnabled(False)
        self.record_options_send_IRPoints = QtGui.QCheckBox("Process data")  
#        self.record_options_send_IRPoints.setEnabled(False)
        
        checkbox_VLayout.addWidget(self.preview_options_triangulate)
        checkbox_VLayout.addWidget(self.record_options_send_video)
        checkbox_VLayout.addWidget(self.record_options_send_IRPoints)
        checkbox_container.setLayout(checkbox_VLayout)
        
        control_layout.addWidget(checkbox_container)
        
        
        control_button_container = QtGui.QWidget()
        control_button_VLayout = QtGui.QVBoxLayout()
                
        self.preview = QtGui.QPushButton("Start Preview")
        self.preview.setObjectName("controlButton")
        self.preview_live = False
        self.preview.clicked.connect(self.toggle_preview_server)
        
        self.start_button = QtGui.QPushButton("Start Recording")
        self.start_button.setObjectName("controlButton")
        self.start_button.clicked.connect(self.start_recording) #Also call the RPi Recording    
        
        back = QtGui.QPushButton("Back")
        back.setObjectName("controlButton")
        back.clicked.connect(self.show_window_1)
        
        control_button_VLayout.addWidget(self.preview)
        control_button_VLayout.addWidget(self.start_button)
        control_button_VLayout.addWidget(back)
        
        control_button_container.setLayout(control_button_VLayout)

        control_layout.addWidget(control_button_container)        
        
        
        control_box.setLayout(control_layout_spacer)
        
        
        #Camera Pane
        
        camera_layout = QtGui.QHBoxLayout()    
        camera_layout.setContentsMargins(0,0,0,0)
        
        #Server Camera
        server_cam_container = QtGui.QWidget() 
        server_cam_VLayout = QtGui.QVBoxLayout()
        
        server_cam_label = QtGui.QLabel("Left Camera")
        server_cam_label.setObjectName("label")
                
        self.label2 = QtGui.QLabel(self) #Label for the server cam image
              
        #Client Camera
        client_cam_container = QtGui.QWidget() 
        client_cam_VLayout = QtGui.QVBoxLayout()

        client_cam_label = QtGui.QLabel("Right Camera")
        client_cam_label.setObjectName("labelClient")
                       
        ###Load temporal images
       
        ###Camera feeds
        image_scale_factor = 0.28
        self.label1 = QtGui.QLabel(self)
        self.label1.setObjectName("camImage")
        self.label2 = QtGui.QLabel(self)
        self.label2.setObjectName("camImage")
        
        f1, f2 =  load_demo_images()
        self.image_size = (int(f1.shape[1] * image_scale_factor), int(f1.shape[0] * image_scale_factor))
        
        f1 = cv2.cvtColor(f1, cv2.COLOR_BGR2RGB)
        f1 = cv2.resize(f1, self.image_size)
        f2 = cv2.cvtColor(f2, cv2.COLOR_BGR2RGB)
        f2 = cv2.resize(f2, self.image_size)
        
        self.image1 = QtGui.QImage(f1, f1.shape[1], f1.shape[0], 
                       f1.strides[0], QtGui.QImage.Format_RGB888)
        
        self.image2 = QtGui.QImage(f2, f2.shape[1], f2.shape[0], 
                       f2.strides[0], QtGui.QImage.Format_RGB888)
                       
        self.label1.setPixmap(QtGui.QPixmap.fromImage(self.image1))
        self.label2.setPixmap(QtGui.QPixmap.fromImage(self.image2))
        self.label1.setAlignment(QtCore.Qt.AlignCenter)
        self.label2.setAlignment(QtCore.Qt.AlignCenter)
        
        
        
        #server_cam_VLayout.addWidget(server_cam_label)
        server_cam_VLayout.addWidget(self.label2)
        
        server_cam_container.setLayout(server_cam_VLayout)
        #client_cam_VLayout.addWidget(client_cam_label)
        client_cam_VLayout.addWidget(self.label1)
        
        client_cam_container.setLayout(client_cam_VLayout)
        
#        server_cam_VLayout.setStretchFactor(self.label1, 10)
#        client_cam_VLayout.setStretchFactor(self.label2, 10)
        
        camera_layout.addWidget(server_cam_container)  
        
        camera_layout.addWidget(client_cam_container)  
        camera_box.setLayout(camera_layout)

        
        
        control_triangLayout = QtGui.QHBoxLayout()
        control_triangLayout.addWidget(triangulation_box)
        control_triangLayout.addWidget(control_box)
        container_grid.addLayout(control_triangLayout)
#        container_grid.addWidget(control_box)
        container_grid.addWidget(camera_box)
        
        
        #Triangulation box
        
        triangulation_layout = QtGui.QVBoxLayout()
        triangulation_layout.setContentsMargins(10,20,10,0)
        
        z_ind_container = QtGui.QWidget()
        z_ind_layout = QtGui.QHBoxLayout()
        
        self.z_ind = positionWidget(500, 1500, 1000, error = 100)
        z_ind_layout.addWidget(self.z_ind)
        
        self.z_ind_label = positionLabel("1000")
        self.z_ind_label.setObjectName("zLabel")
 
        self.z_ind_label.setAlignment(QtCore.Qt.AlignCenter)
#        z_ind_label.setStyleSheet(""" QLabel {background-color: rgb(16, 159, 221);}""")
#        z_ind_label.setContentsMargins(0,0,0,0)
        
        z_ind_layout.addWidget(self.z_ind_label)     
        
        z_ind_container.setLayout(z_ind_layout)
        triangulation_layout.addWidget(z_ind_container)
        triangulation_layout.addSpacing(75)
        
        
        triangulation_box.setLayout(triangulation_layout)
        
        
        return self.camera_container


    def create_processing_group(self):
        """Create the data processing. Controls the layout and creates all the necessary widgets"""
        
        self.processingBox = QtGui.QGroupBox("Data Processing")
        
        processing_layout = QtGui.QHBoxLayout()     
        
        tab_layout = QtGui.QVBoxLayout()
        
        processing_tabs = QtGui.QTabWidget()        
        self.tab1 = QtGui.QWidget()
        self.tab2 = QtGui.QWidget()
        self.tab3 = QtGui.QWidget()        
        self.tab1_UI()       
        self.tab2_UI()
        
        processing_tabs.addTab(self.tab1, "Console")
        processing_tabs.addTab(self.tab2, "Markers")
        processing_tabs.addTab(self.tab3, "3D Markers")
        
        processing_button_layout = QtGui.QHBoxLayout() 
        process_data_button = QtGui.QPushButton("Process data")
#        process_data_button.clicked.connect(self.process_selected_data)
        process_data_button.clicked.connect(self.process_selected_data_thread)
        reload_dir_button = QtGui.QPushButton("Reload data directory")
        reload_dir_button.clicked.connect(self.load_directory)
        exit_process_button = QtGui.QPushButton("Exit")
        exit_process_button.clicked.connect(self.show_window_1)
        
        processing_button_layout.addWidget(process_data_button)
        processing_button_layout.addWidget(reload_dir_button)
        processing_button_layout.addWidget(exit_process_button)
        
        tab_layout.addWidget(processing_tabs)        
        tab_layout.addLayout(processing_button_layout)
        
         
        
        get_dir_button = QtGui.QPushButton("Refresh data directory")
        get_dir_button.clicked.connect(self.load_directory) #Fails to wipe the current tree (BUG). Removed for the moment
        
        
#        process_data_button.clicked.connect(self.process_data_popup) #Start the process data popup
        self.all_records = None #Becomes a list in later functions. If none then later functions wont execute
        
        self.pointListBox = QtGui.QTreeWidget() #Show all the files in a directory with this
        self.pointListBox.itemClicked.connect(self.record_clicked)
        header=QtGui.QTreeWidgetItem(["Recorded_data"])
        self.pointListBox.setHeaderItem(header)   #Another alternative is setHeaderLabels(["Tree","First",...])
#        self.load_directory()

#        processTab = QtGui.QTabWidget()
#        tab1 = QtGui.QWidget()
#        tab2 = QtGui.QWidget()
#        tab3 = QtGui.QWidget()
		
#        processTab.addTab(tab1,"3d Data")
#        processTab.addTab(tab2,"Tab 2")
#        processTab.addTab(tab3,"Tab 3")

        processing_layout.addWidget(self.pointListBox)
        processing_layout.addLayout(tab_layout)
#        processing_layout.addWidget(processing_tabs)
#        processing_grid = QtGui.QGridLayout()          
        
#        demographics_grid.addWidget(New_participant, 0, 0, 1, 1)
        
#        processing_grid.addWidget(get_dir_button, 5,0, 1,1)
#        processing_grid.addWidget(process_data_button, 5,1, 1,1)    
#        processing_grid.addWidget(self.pointListBox, 0, 0, 5, 5)
#        processing_grid.addWidget(processTab, 0, 1, 5, 2)
#        processing_grid.setSpacing(10)
        
        self.processingBox.setLayout(processing_layout)
        return self.processingBox
        
    def record_clicked(self):
        """Emit a signal with the directory of the clicked record (from the treeWidget of all loaded records)"""
        
        current_item= self.pointListBox.currentItem()
        
        for rec, rec_name in self.all_records:
            
            if rec == current_item:
                
                self.record_item_clicked.emit(rec_name)
                self.update_marker_tab(rec_name)
                print(rec_name)
                break
        
    def update_marker_tab(self, rec_name):
        """Get the data for a record and use it to plot the marker tab"""
        
        if '3d_filtered.csv' in os.listdir(rec_name):
            
            filt_data = np.loadtxt(os.path.join(rec_name, '3d_filtered.csv'), delimiter=',', skiprows = 1) #Load an array of markers
            filt_data = filt_data.reshape(filt_data.shape[0], int(filt_data.shape[1] / 3), 3) #Reshape into an NxMX3 array (points, marker, axis)
            marker_mid_3d_filt = np.sum(filt_data, axis = 1)/2.0

            non_filt_data = np.loadtxt(os.path.join(rec_name, '3d_unfiltered.csv'), delimiter=',', skiprows = 1) #Load an array of markers
            non_filt_data = non_filt_data.reshape(non_filt_data.shape[0], int(non_filt_data.shape[1] / 3), 3) #Reshape into an NxMX3 array (points, marker, axis)
            non_marker_mid_3d_filt = np.sum(non_filt_data, axis = 1)/2.0

        

            marker_mid_3d_filt[marker_mid_3d_filt == -999] = np.nan
            non_marker_mid_3d_filt[non_marker_mid_3d_filt == -999] = np.nan

            dist = np.sqrt(np.sum(np.square(np.diff(marker_mid_3d_filt, axis = 0)), axis = 1))
            
#            ax[0].plot(marker_mid_3d[:,0])
            self.ax[0].cla()
            self.ax[1].cla()
            self.ax[2].cla()
            self.ax[3].cla()
            
            self.ax[0].plot(non_marker_mid_3d_filt[:,0], 'r')
            self.ax[1].plot(non_marker_mid_3d_filt[:,1], 'r')
            self.ax[2].plot(non_marker_mid_3d_filt[:,2], 'r')
            
            self.ax[0].plot(marker_mid_3d_filt[:,0])
            self.ax[1].plot(marker_mid_3d_filt[:,1])
            self.ax[2].plot(marker_mid_3d_filt[:,2])
            
            self.ax[3].plot(dist, 'k')
            self.ax[3].fill_between(range(dist.shape[0]), 0, dist, color = 'r', alpha = 0.5)
            
            
            [self.ax[i].get_xaxis().set_visible(False) for i in range(3)]
            
            self.canvas.draw()
            
        else:
            print("no files")
    
#        self.ax[0].plot(data, '*-')
        
        
    def tab1_UI(self):
        
        console_layout = QtGui.QHBoxLayout() 
        
        self.processing_console = Console()        
        console_layout.addWidget(self.processing_console)        
        self.tab1.setLayout(console_layout)        
        
        #Signals for the console.
        self.data_dir_set.connect(self.processing_console.promt_select_data)
        self.data_dir_set.connect(self.load_directory)
        
    def tab2_UI(self):
        
        figure_layout = QtGui.QHBoxLayout()
        # a figure instance to plot on
        sns.set_style("white")
        
        self.figure, self.ax = plt.subplots(4,1, sharex = True, figsize = (3, 3))
        # this is the Canvas Widget that displays the `figure`
        # it takes the `figure` instance as a parameter to __init__
        self.canvas = FigureCanvas(self.figure)
#        data = [random.random() for i in range(10)]

        # create an axis
#        self.ax = self.figure.add_subplot(111)

        # discards the old graph
#        self.ax.hold(False)

        # plot data
#        self.ax[0].plot(data, '*-')
#        sns.despine()
        # refresh canvas
#        self.canvas.draw()    
        
        figure_layout.addWidget(self.canvas)
        
        self.tab2.setLayout(figure_layout) 
        
     
    def show_window_1(self):
        """Show the demographics window"""
        self.window_live = 1
#        self.demographicsBox.show()
#        self.camera_box.hide()
#        self.recording_box.hide()
        self.camera_container.hide()
        self.demographics_container.show()
        self.show_keyboard()
        self.processingBox.hide()
        self.timer.start(33) ##Start the timer that controls the scrolling text on the menubar
        
        if self.preview_live:
            self.toggle_preview_server()        
    
    def show_window_2(self):        
        """Show the camera preview window"""
        self.window_live = 2
        self.get_demographics()
        
        if self.camera_backend_live:
            
            self.timer.stop() #Stop the timer that controls the scrolling text on the menubar
            self.camera_container.show()
            self.demographics_container.hide()
    
            self.hide_keyboard()
            self.processingBox.hide()
            
            if not self.preview_live:
                self.toggle_preview_server()
                
        elif debug == True: 
            
            self.timer.stop() #Stop the timer that controls the scrolling text on the menubar
            self.camera_container.show()
            self.demographics_container.hide()
    
            self.hide_keyboard()
            self.processingBox.hide()
            
            if not self.preview_live:
                self.toggle_preview_server()
        
        else:
            print("Camera Backend not live")
 
        
    def show_window_3(self):        
        """Show the data processing window"""
        self.window_live = 3
#        self.timer.stop()#Stop the timer that controls the scrolling text on the menubar
        self.camera_container.hide()
        self.demographics_container.hide()
        self.load_directory()
        self.processingBox.show()
#        self.demographicsBox.hide()
#        self.camera_box.hide()
#        self.recording_box.hide()
        self.hide_keyboard()
      
        if self.preview_live:
            self.toggle_preview_server()

         
    def create_keyboard(self):
        """Create the GUI keyboard instance and connect the keys to all the objects the keyboard needs to interact with"""
        
        self.keyboard = virtualKeyboard() #Create a touch screen keyboard instance
        
        #NOW CONNECT ALL THE KEYS TO THEIR OUTPUTS
        self.keyboard.connect_to_buttons(self.Forename_edit.recieve_input) #Connect this to the buttons
        self.keyboard.connect_to_buttons(self.Surname_edit.recieve_input) #Connect this to the buttons
        self.keyboard.connect_to_buttons(self.ID_edit.recieve_input) #Connect this to the buttons
        self.keyboard.connect_to_buttons(self.Condition_edit_line.recieve_input)
#        self.keyboard.connect_to_buttons(self.DOB_edit.recieve_input) #Connect this to the buttons
        
        self.keyboard.connect_to_buttons(self.Record_Time.recieve_input)
        
        self.Forename_edit.text_length.connect(self.keyboard.cap_zero_len)
        self.Surname_edit.text_length.connect(self.keyboard.cap_zero_len)
        self.ID_edit.text_length.connect(self.keyboard.cap_zero_len)
#         spacebar.pressed.connect(self.Forename_edit.recieve_input)
        return self.keyboard
            

    def show_keyboard(self):
        """Show the touch screen keyboard"""
        print("SHOW")
        self.keyboard.show()
        
    def hide_keyboard(self):
        """Hide the touch screen keyboard"""
        self.keyboard.hide()
        print("HIDE")
        
    def getDOB(self):
        """Launch a QDialog window to get the DOB for the participant"""
#        #DOB should be a date format or a box to select the date
        self.d = myDateDialog(self) 
#        self.d.move(50,50)
        self.d.exec_()
     
        if self.d.result() == 0:
            DOB_val = self.d.save()
#            DOB_val = DOB_val.toPyDateTime()
#            DOB_str = DOB_val.strftime('%d/%m/%Y')
            self.DOB_edit.setText(DOB_val)
        
               
        
    ##---------------------------------------------##
	##---------------------------------------------##       
	##----------Participant List Functions---------##        
	##---------------------------------------------##        
	##---------------------------------------------##        
	##---------------------------------------------##
	##---------------------------------------------##
            
            
            
    def toggle_load_part_button(self):
        """
       	Menbar functionfunction: Load a .csv file of a participant list. 
        A participant list is a csv file containing demographic and record options for all the participants in a study. 
        Toggles the load participant button. If no participant list loaded it will open a window to select a participant list.
        Otherwise it will remove the currently loaded participant list and clear the participant information
        """
        
        print(self.part_listMenu.text())
        if self.part_listMenu.text() == "&Load Participant List":
            
            self.load_file() #Load the participant list
            
            if self.participant_list_fname != '':
                self.new_participant() #Get rid of anything in the demographics windows
                self.part_listMenu.setText("&Remove Participant List") #Rename the unload button
                
                #Disable editing of demographics
                self.Forename_edit.toggle_enable() 
                self.Surname_edit.toggle_enable()
                self.Record_Time.toggle_enable()
                self.Gender_edit.setEditable(False)
                self.ConditionStack.setCurrentIndex(0)
        
        else:
            
            self.participant_list_loaded = False
            self.new_participant()
            self.part_listMenu.setText("&Load Participant List")
            
            #Enable editing of demographics
            self.Forename_edit.toggle_enable()
            self.Surname_edit.toggle_enable()
            self.Record_Time.toggle_enable()
            self.ConditionStack.setCurrentIndex(1)
            
            
    def load_file(self):
        """Open a dialog to select a .csv file which contains a participant list. This list contains all the participant information for a given experiment
        This function is called by self.toggle_load_part_button"""
        self.participant_list_fname = ''
        #IF this fails it probably needs a [0] after the next line. Needs removing to use with PyQt
        
        
        if onDesktop:
            self.participant_list_fname = QtGui.QFileDialog.getOpenFileName(self, 'Open file', 
                self.storage_loc)
        else:            
            self.participant_list_fname = QtGui.QFileDialog.getOpenFileName(self, 'Open file', 
                    self.storage_loc)[0]
        
        #Check that a file was selected and load the file
        
        if self.participant_list_fname != '':
           
            self.participant_list = pd.read_csv(self.participant_list_fname)
            self.participant_list_loaded = True
    
            print(self.participant_list_fname[0])
            
            ##Add a completer to the ID_edit (NOTE: Only works when typing with read keyboard. Needs bug fix)        
#            completer = QtGui.QCompleter()
#            self.ID_edit.setCompleter(completer)      
#            model = QtGui.QStringListModel(list(self.participant_list['ID'].unique()))        
#            completer.setModel(model)        
#            self.ID_edit.textChanged.connect(completer.setCompletionPrefix)    
         
    def new_participant(self):
        """Menubar function:
            Remove all the participant data from the demographics screen"""
        print("NEW PARTICIPANT")
        
        self.Forename_edit.reset_text()
        self.Surname_edit.reset_text()
        self.ID_edit.reset_text()
        self.DOB_edit.reset_date()
        
        self.Condition_edit.clear()
        
        self.Record_Time.set_text("30")
        
    def find_participant(self):
        """Demographics screen function:
            Find a participant from a loaded participant list given the participant number that has been typed in"""
   
        self.participant_found = True
        
        ID = self.ID_edit.text() #Get the ID QLineEdit text (Case sensitive)
        
        if self.participant_list_loaded:
            
            
            part_data = self.participant_list[self.participant_list['ID'].astype(str) == str(ID)]
            
            N_entries = part_data.shape[0] #Number of entries for that participant
            
            if N_entries == 0:
                
                message_box = QtGui.QMessageBox()
                message_box.setText("ID not found in the participant list\nRemember ID is case sensitive")
                message_box.setIcon(QtGui.QMessageBox.Information)                
                message_box.exec_()
                
            else:
                self.current_entry_index = part_data.index[0] #Get the first index value

                part_forename = self.participant_list.loc[self.current_entry_index]['Forename']
                part_surname = self.participant_list.loc[self.current_entry_index]['Surname']
                
                part_DOB = self.participant_list.loc[self.current_entry_index]['DOB']
                part_Gender = self.participant_list.loc[self.current_entry_index]['Gender']
                part_recTime = int(self.participant_list.loc[self.current_entry_index]['Recording_Time'])
                print(ID, part_forename, part_surname, part_DOB, part_Gender, part_recTime)  
                
                
                #Now set the QLine Edits to these
                self.Forename_edit.setText(part_forename)
                self.Forename_edit.text2 = part_forename #This stops keyboard delete removing the entire entry
                
                self.Surname_edit.setText(part_surname)
                self.Surname_edit.text2 = part_surname
                
                self.Record_Time.set_text(str(part_recTime))
#                self.Record_Time.set_text('Hi')
#                self.Record_Time.text2 = part_recTime
                
                if part_Gender.upper() == 'M':
                    self.Gender_edit.setCurrentIndex(0)
                elif part_Gender.upper() == 'F':
                    self.Gender_edit.setCurrentIndex(1)
                    
                self.DOB_edit.setText(part_DOB)
                
                
                
                self.Condition_edit.clear()
                    
#                for entry in part_data['Condition'].values:
#                    self.Condition_edit.addItem(entry)
                    
                
                for e in range(len(part_data)):
                    
                    entry = part_data.iloc[e]
                    
                    self.Condition_edit.addItem(entry['Condition'])                 
                    
#                print(len(part_data))                    
            
        else:
            print("Load a participant list first")
            message_box = QtGui.QMessageBox()
            message_box.setText("No participant list loaded")
            message_box.setIcon(QtGui.QMessageBox.Information)                
            message_box.exec_()
            
        
            
            
        
    def change_condition(self):
        
        """Demographics window function:
            Load all the conditions for a given participant and display them in the condition drop down box
            Note: Causing IndexError loading the participant. Probably hasn't changed the inline text edit by this point        
        """        
        
        ID = self.ID_edit.text() #Get the ID QLineEdit text (Case sensitive)
        
        if self.participant_list_loaded:
                        
            part_data = self.participant_list[self.participant_list['ID'].astype(str) == str(ID)]    
            
            condition = self.Condition_edit.currentText()
            
            if condition == '':
                print("NO CONDITION SELECTED")  #Bit of a hack. Stops an error being thrown because this function is called when a participant is loaded up (erroneously) and when the condition is changed (working correctly)
                return
                
            part_data_cond = part_data[part_data['Condition'] == condition]
            self.current_entry_index = part_data_cond.index[0]
           
            part_recTime = int(part_data_cond['Recording_Time'].values[0])
        
#            self.Record_Time.set_text("HI")
            self.Record_Time.set_text(str(part_recTime))
#            self.Record_Time.text2 = part_recTime
    

    def update_participant_list(self):
        """Call at the end of recording. If self.participant_list is loaded then update the last recording entry to recorded"""
        
  
        if self.participant_list_loaded:
            
            self.participant_list.loc[self.current_entry_index, 'Run'] = 1 #Once the recording has happened set the Run to 1
            
            self.participant_list.to_csv(self.participant_list_fname, index = False) #Update the participant list file


    def check_participant_not_run(self):
        """Checks if this participant entry has already been run"""
        
        if self.participant_list_loaded:
            if self.participant_list.loc[self.current_entry_index, 'Run'] == 1:       
                
                message_box = QtGui.QMessageBox()
                message_box.setText("This participant entry was already run\n")
                message_box.setIcon(QtGui.QMessageBox.Information)                
                message_box.exec_()
                
                return True           
                
      ##---------------------------------------------##
	##---------------------------------------------##       
	##---------------Data Processing---------------##        
	##---------------------------------------------##        
	##---------------------------------------------##        
	##---------------------------------------------##
	##---------------------------------------------##             
    
    
      
    def load_directory(self):
        """Load a directory tree to show all the records than can be processed
        Allows the operator to select data to analyse using a tree
        """
        
        if self.storage_loc != '':            
        
            data_directory = os.path.join(self.storage_loc, 'recorded_data') 
         
        else: 
            return
        
        print("Loading data")
#        experiments = glob.glob(os.path.join(data_directory, '*'))
        self.pointListBox.clear() #Clear the treewidget
        self.all_records = []
        
            
        name = 'Select All'
        parent = QtGui.QTreeWidgetItem(self.pointListBox)
        parent.setText(0, "{}".format(name))
        parent.setFlags(parent.flags() | QtCore.Qt.ItemIsTristate | QtCore.Qt.ItemIsUserCheckable)
     
        participants = glob.glob(os.path.join(data_directory, '*'))
        
        for part in participants:
            print(part)
            if not os.path.isdir(part):
                print("{} is not a directory".format(part))
                continue
            p_name = os.path.split(part)[-1]
            child = QtGui.QTreeWidgetItem(parent)
            child.setFlags(child.flags() | QtCore.Qt.ItemIsTristate | QtCore.Qt.ItemIsUserCheckable)
            child.setText(0, "Participant: {}".format(p_name))
            child.setCheckState(0, QtCore.Qt.Unchecked)
            
            records = glob.glob(os.path.join(part, '*'))
            
            for rec in records:
#                print(rec)
                r_name = os.path.split(rec)[-1]
                cond_name = pd.Series.from_csv(os.path.join(rec, 'demographics.csv'))['condition']
                child2 = QtGui.QTreeWidgetItem(child)
                child2.setFlags(child2.flags() | QtCore.Qt.ItemIsUserCheckable)
                child2.setText(0, "{}: {}".format(r_name, cond_name))
                child2.setCheckState(0, QtCore.Qt.Unchecked)
                
                self.all_records.append([child2, rec])
      
        self.pointListBox.expandAll() 
        self.pointListBox.update()

    def get_N_records_to_process(self):
        """return the number of participants to process"""
        self.n_records_to_process = 0
        if not isinstance(self.all_records, type(None)):
            
            for rec, rec_name in self.all_records:
                
                if rec.checkState(0) == 2:
                    print(rec_name)
                    self.n_records_to_process += 1
                    
        return self.n_records_to_process
                    
    def process_selected_data_thread(self):
        """A thread wrapper for self.process_selected_data"""
        self.n_records = self.get_N_records_to_process()
        self.processing_console.promt_process_data(self.n_records) 
        
        
        self.processing_live = True        
        self.record_text = 'Preparing to process'
        old_text = self.record_text
        self.process_thread = threading.Thread(target = self.process_selected_data)
        self.process_thread.start()
        
        print("Thread started")              
       
        while self.processing_live:
            
            if self.record_text != old_text:
            
                self.processing_console.addText(self.record_text)
                old_text = self.record_text             
            
            #Add a progress bar or loading overlay
            QtGui.QApplication.processEvents() #Update the GUI            
            
#        self.processing_console.clearConsole()                   
        self.processing_console.addText("Processing finished") 
        self.processing_console.addText("It took {} seconds to process {} records".format(int(self.process_time), self.n_records)) 
        
    def process_selected_data(self):
        """Process all the selected data in the processing GUI"""        
               
        proc_count = 1
        
        fos = FileOrderingSystem() #File processing system object
        
        t0 = time.time()
        if not isinstance(self.all_records, type(None)):
            
            for rec, rec_name in self.all_records:
                
                if rec.checkState(0) == 2:                    
            
                    self.record_text = "Processing Record {} of {}".format(proc_count, self.n_records)
#                    self.processing_console.addText("Processing Record {} of {}".format(proc_count, n_records))
                    
                    p_nan = self.process_file(rec_name, parallel = True)
                    self.record_text = "{0:.0f}% of frames had missing markers\n".format(p_nan)
                    time.sleep(0.25)
                    proc_count += 1
       
        t1 = time.time()
        
        
#        
#        self.processing_console.addText("Creating summary file")   
        self.create_summary_file()
#        self.processing_console.addText("Processing finished")        
        self.process_time = t1 - t0
        self.processing_live = False       

        
        
    def process_file(self, rec_name, parallel = True):
        """Process the data from a specific record:
            rec_name: the folder containing a specific record
            parallel: Boolean - process the videos on multiple cores"""
            
        print("THE REC NAME\n{}".format(rec_name))
        client_markers, server_markers = self.process_video_files(rec_name, parallel = parallel) #Get the markers from each video file 
    
        p_nan_points, PL_mid = self.process_marker_data(client_markers, server_markers, rec_name)
            
        return p_nan_points
        
    def process_video_files(self, rec_name, parallel = True):
        """Process the video files to obtain the marker positions in the the videos"""
        #Load the record's video files for processing
        self.proc = backend.posturalProc(v_fname = os.path.join(rec_name, 'videos', 'testIR.h264'), calibration_dir = os.path.join(rec_name, 'calibration'), kind = 'client')
        self.proc2 = backend.posturalProc(v_fname = os.path.join(rec_name, 'videos', 'testIR_server.h264'), calibration_dir = os.path.join(rec_name, 'calibration'), kind = 'client')
        
        
        if parallel:
            #Process the markers (in parallel)?
            client_queue = multiprocessing.Queue()
            server_queue = multiprocessing.Queue()
            print("Starting IR marker processes")
            p1 = multiprocessing.Process(target=self.proc.get_ir_markers, kwargs={'out_queue' : client_queue})
            p2 = multiprocessing.Process(target=self.proc2.get_ir_markers, kwargs={'out_queue' : server_queue})
            
            p1.start()
            p2.start()
            
            client_markers = client_queue.get()
            server_markers = server_queue.get()
                   
            p1.join()
            p2.join()
            print("Finished IR marker processes")

   
        else:       
     
            client_markers = self.proc.get_ir_markers()
            server_markers = self.proc2.get_ir_markers()

        return client_markers, server_markers
        
    
    def process_marker_data(self, client_markers, server_markers, rec_name):
        """Stereo triangulate the marker positions and then save everything to disk"""
        
        
        #Process markers        
        proc_all_markers = ir_marker.markers2numpy(client_markers) 
        proc2_all_markers = ir_marker.markers2numpy(server_markers)    

        #Ensure the marker arrays are the same size. It may be that one of the cameras ran for a frame or two more
        #Similtaneously remove the first second of records
        #min_n_markers = np.min([proc_all_markers.shape[0], proc2_all_markers.shape[0]])
        #proc_all_markers = proc_all_markers[60:min_n_markers] #removes the first 60 frames (1 second recording)
        #proc2_all_markers = proc2_all_markers[60:min_n_markers] #removes the first 60 frames (1 second recording)   
        
#        #Save marker data in the records data directory
#        np.save(open(os.path.join(rec_name, 'client_IRpoints.npy'), 'wb'), proc_all_markers)
#        np.save(open(os.path.join(rec_name, 'server_IRpoints.npy'), 'wb'), proc2_all_markers)
        
        #Save the marker data as csv files
        cam_marker_headers = ['m{0}_x,m{0}_y'.format(i) for i in range(int(proc_all_markers.shape[1]))]
        cam_marker_headers = ",".join(cam_marker_headers)        
        proc_all_markers_reshape = proc_all_markers.reshape(proc_all_markers.shape[0], np.prod(proc_all_markers.shape[1:]))
        proc2_all_markers_reshape = proc2_all_markers.reshape(proc2_all_markers.shape[0], np.prod(proc2_all_markers.shape[1:]))         
        
        np.savetxt(os.path.join(rec_name, 'client_IRpoints.csv'), proc_all_markers_reshape, header = cam_marker_headers, delimiter = ',', comments='', fmt='%1.4f')
        np.savetxt(os.path.join(rec_name, 'server_IRpoints.csv'),  proc2_all_markers_reshape, header = cam_marker_headers, delimiter = ',', comments='', fmt='%1.4f')
        
              
        #Perform stereo triangulation
        try:
            stereo =  backend.stereo_process(self.proc, self.proc2, calibration_dir = os.path.join(rec_name, 'calibration')) 
        except AttributeError:            
            print("LOADING CAL DATA")
            self.proc = backend.posturalProc(v_fname = os.path.join(rec_name, 'videos', 'testIR.h264'), calibration_dir = os.path.join(rec_name, 'calibration'), kind = 'client')
            self.proc2 = backend.posturalProc(v_fname = os.path.join(rec_name, 'videos', 'testIR_server.h264'), calibration_dir = os.path.join(rec_name, 'calibration'), kind = 'client')
            stereo = backend.stereo_process(self.proc, self.proc2, calibration_dir = os.path.join(rec_name, 'calibration')) 

              
        markers3d = stereo.triangulate_all_get_PL(proc_all_markers, proc2_all_markers)
        markers3d_filt = stereo.kalman_smoother(markers3d) #Kalman smooth marker positions (Filtering)
        
#        markers3d_filt = stereo.zero_order_butterworth(markers3d) #Test out butterworth filter
        
        marker_mid_3d = np.sum(markers3d, axis = 1)/2.0 #Calculate the mid point of the two markers
        marker_mid_3d_filt = np.sum(markers3d_filt, axis = 1)/2.0 #Calculate the mid point of the two (filtered) markers        
        distance_between_leds_filt = np.sqrt(np.sum(np.square(np.diff(markers3d_filt, axis = 1)), axis = 2)).squeeze() #Calculate the distance between the IR-LED's
        p_nan_points = 100 * (np.isnan(markers3d)[:,0,0].sum() / markers3d.shape[0]) #The number of missing markers
        #Prepare the marker data for file
        reshape3d = markers3d.reshape(markers3d.shape[0], np.prod(markers3d.shape[1:])) #Markers 3d reshaped
        filt_reshape3d =  markers3d_filt.reshape(markers3d_filt.shape[0], np.prod(markers3d_filt.shape[1:])) #Markers 3d filtered reshaped
        
        #Write any NaN values as -999
        reshape3d[np.isnan(reshape3d)] = -999
        filt_reshape3d[np.isnan(filt_reshape3d)] = -999
                       
        headers = ['m{0}_x,m{0}_y,m{0}_z'.format(i) for i in range(int(reshape3d.shape[1]/3))]
        headers = ",".join(headers)
        #Save the triangulated 3D data to the records data directory
        np.savetxt(os.path.join(rec_name, '3d_unfiltered.csv'), reshape3d, header = headers, delimiter = ',', comments='', fmt='%1.4f')
        np.savetxt(os.path.join(rec_name, '3d_filtered.csv'), filt_reshape3d, header = headers, delimiter = ',', comments='', fmt='%1.4f')
        np.savetxt(os.path.join(rec_name, 'distance_between_LEDs.csv'), distance_between_leds_filt, header = headers, delimiter = ',', comments='', fmt = '%1.4f')
        
        np.savetxt(os.path.join(rec_name, "mid3D_unfiltered.csv"), marker_mid_3d, header = 'x,y,z', delimiter = ',', comments = '', fmt = '%1.4f')
        np.savetxt(os.path.join(rec_name, "mid3D_filtered.csv"), marker_mid_3d_filt, header = 'x,y,z', delimiter = ',', comments = '', fmt = '%1.4f')
        
        #Calculate the path length metrics
        PL = np.sum(np.sqrt(np.sum(np.square(np.diff(markers3d_filt, axis = 0)), axis = 2)), axis = 0)
        displacement_mid = np.sqrt(np.sum(np.square(np.diff(marker_mid_3d_filt, axis = 0)), axis = 1))
        PL_mid = np.sum(displacement_mid, axis = 0)
        
        #Save a summary file of all the participants metrics
        summary = pd.Series({'PL1':PL[0], 'PL2':PL[1], 'MID':PL_mid, 'MID_mean': np.mean(displacement_mid)})
        summary.to_csv(os.path.join(rec_name, 'summary.csv'))

        return p_nan_points, PL_mid       
        
    def create_summary_file(self):        
        """Create a summary file of all the data that has been markered for processing""" 
  
        
        master_dataFrame = pd.DataFrame()
        
        for rec, rec_name in self.all_records:
                
            if rec.checkState(0) == 2:
                
                summary = pd.Series.from_csv(os.path.join(rec_name, 'summary.csv'))
                demographics = pd.Series.from_csv(os.path.join(rec_name, 'demographics.csv'))
                     
                joined = pd.concat((demographics, summary))
            
                master_dataFrame = master_dataFrame.append(joined, ignore_index = True)
                
 
        master_dataFrame.to_csv( os.path.join(self.storage_loc, 'recorded_data', 'master_data.csv')) #Save a csv of the summarised data
#                print(summary)
#                print(demographics)
                    
                    
   

	##---------------------------------------------##
	##---------------------------------------------##       
	##----------Camera Feed Preview Functions------##        
	##---------------------------------------------##        
	##---------------------------------------------##        
	##---------------------------------------------##
	##---------------------------------------------##
    
    
    
    def toggle_preview_server(self):
        """Toggle the server video preview on and off"""
        
        if onDesktop:
            return
            
        print(self.preview_live)
    
        if self.preview_live:
            
            print("Request End Preview")
            self.preview_live = False
            self.end_preview() 
            self.preview.setText("Start Preview")
            
            print(self.preview_live)
            
        elif not self.preview_live:
            
            print("ON TOGGLE")
            self.preview_live = True  
            self.preview.setText("Stop Preview")
            self.start_preview()
                      
       
    def preview_triangulate(self, img1, img2):
        """Report the position of any markers visable in the preview"""        
        
        ir1 = ir_marker.find_ir_markers(img1, n_markers = 3, it = 0, tval = 150, last_markers = None, plot_loc = None)
        ir2 = ir_marker.find_ir_markers(img2, n_markers = 3, it = 0, tval = 150, last_markers = None, plot_loc = None)
        
        
        if ir1!= None:
            
            for mark in ir1:
                 
#                 print(mark['pos'], mark['radius'])
                 cv2.circle(img1, (int(mark['pos'][0]), int(mark['pos'][1])), int(mark['radius']), (255, 0, 0), 10)
        
        if ir2!= None:
            
            for mark in ir2:
                 
#                 print(mark['pos'], mark['radius'])
                 cv2.circle(img2, (int(mark['pos'][0]), int(mark['pos'][1])), int(mark['radius']), (255, 0, 0), 10)
             
        
        #3d marker tracking
        if (ir1 != None) and (ir2 != None):
            ir1 = ir_marker.markers2numpy([ir1]) #Pass as list
            ir2 = ir_marker.markers2numpy([ir2])

            markers3d = self.stereo.triangulate_all_get_PL(ir1, ir2).squeeze() #Get the marker positions in 3d space 
          
            
            self.marker_mid = np.sum(markers3d, axis = 0)/2.0
       
            #Calculate the distance of the marker from the center of the two camereas. Calculate the vector between the midpoint along T and the observed point. Then take it's magnitude
            marker_distance = vector_magnitude(self.marker_mid - (self.stereo.T.flatten()/2.0)) 
            
            self.z_ind.setValue(marker_distance)
            self.z_ind_label.setText(str(int(marker_distance)))
    
        return img1, img2
    
    def start_preview(self):
        """Start the camera preview from the server"""
                
           
        clientPreviewProc = backend.posturalProc(kind = 'client_preview')
        serverPreviewProc = backend.posturalProc(kind = 'server_preview')
        self.stereo =  backend.stereo_process(clientPreviewProc, serverPreviewProc) 
        
        self.backend_camera.TCP_client_request_videoPreview() #Request video preview from server         
        self.backend_camera.videoPreview() #Request video preview from client
        
        
       
        
        while self.preview_live:
            
            
            #Poll the latest camera images
            f1 = self.backend_camera.poll_videoPreview()       
            f2 = self.backend_camera.TCP_client_poll_videoPreview()
                        
            #Draw markers to screen and trinagulate
            if self.preview_options_triangulate.isChecked() and (f1 != None) and (f2 != None):

                f1, f2 = self.preview_triangulate(f1,f2)                  
            
            
            if (f1 == 'DEAD') or (f2 == "DEAD"):
                print("DEADDDDD")
                break
            
            ##Hand videos to rendering functions            
            if f1 != None:

                self.render_preview(f1, self.label1)
                                
                
            if f2 != None:
                self.render_preview(f2, self.label2)              
                
                
            #Update the images
            QtGui.QApplication.processEvents() 
        
    def end_preview(self):
        """End the video preview"""
        self.backend_camera.TCP_client_stop_videoPreview()
        self.backend_camera.stop_videoPreview()
        
        
    def render_preview(self, frame, Qobj):
        """pass a frame and a QLabel object and render the frame to it""" 

                 
        img = cv2.resize(frame, self.image_size) #Resize the image        
        
        
     
        image2 = QtGui.QImage(img, img.shape[1], img.shape[0], 
                       img.strides[0], QtGui.QImage.Format_RGB888)
        
        ctypes.c_long.from_address(id(img)).value = 1 #This allows the garbage collector to release the memory used here. Fixes memory leak
        
        Qobj.setPixmap(QtGui.QPixmap.fromImage(image2))

    
      
        
    ##---------------------------------------------##
	##---------------------------------------------##       
	##---------Camera Recording Functions----------##        
	##---------------------------------------------##        
	##---------------------------------------------##        
	##---------------------------------------------##
	##---------------------------------------------##
                    
    
    def start_recording(self):
        """Will start the RPi Recording"""        
        
        run = self.check_participant_not_run() #Open a pop up window if the participant has been run
        
        if run:
            
            return
        
            #Check a storage location has been set
        if self.storage_loc == '':
            storage_msgBox = QtGui.QMessageBox()
            storage_msgBox.setText("""A storage location has not been set.\n\nSelect a storage location by clicking Data Control -> Set Save Directory""" )
            storage_msgBox.exec_()
            return
            
        self.recording_Terminate = False        
        
        self.start_button.setText("Recording")
        #Update the images
        QtGui.QApplication.processEvents() 
        
        if self.preview_live:
            self.toggle_preview_server() #If we are in preview mode close the preview first
            
        t = self.Record_Time.value()
        print("RECORD NOW FOR {}".format(t))
        
#        progress_thread = threading.Thread(target = self.progressBar_update, args = (t,))
#        progress_thread.start()
        print("REQUEST RECORDING")
        self.backend_camera.TCP_client_start_UDP(t, 'testIR.h264') #Starts the video recording       
        
        #Video is finished
        self.post_recording_protocol_progressBar() #Place files in correct place
        
    
    def post_recording_protocol(self, callback_function = None):

        
        self.transfer_prof_text = "Transferring time stamps..."
        
        self.backend_camera.TCP_client_request_timestamps() #Request time stamps
        
        self.transfer_prof_text = "Validating time stamps..."
        
        self.ts_error = self.check_timestamp_error() #Check if there are any problems with the time stamps   
        
        if self.ts_error:
            print("TSEROR")
            self.data_transfer_complete = True
            return #Return before the other files are sent if there is an error with the timestamps

        if self.record_options_send_video.isChecked():
            self.transfer_prof_text = "Transferring videos..."
            
            self.backend_camera.TCP_client_request_video() #Request video
           

        if self.record_options_send_IRPoints.isChecked():        
            self.transfer_prof_text = "Processing marker data..."
            client_ir_points, server_ir_points = self.backend_camera.TCP_client_request_IRPoints(self.update_progress_value) #Request the IR points (Will process the data)
                
      
        self.transfer_prof_text = "Updating participant list..."         
        self.update_participant_list() #Update the participant list csv to recorded for this entry
      
        self.transfer_prof_text = "Archiving files..."      
        rec_dir = self.archive_files() #Archive the files and return the recording directory
        

        if self.record_options_send_IRPoints.isChecked():    
            self.transfer_prof_text = "Triangulating marker data..."            
            self.p_nan_points, self.PL_mid = self.process_marker_data(client_ir_points, server_ir_points, rec_dir) #Triangulate the marker data
                 
        self.data_transfer_complete = True
        
        return    	
        
    def post_recording_protocol_progressBar(self):
        """Get the files back from the server pi and put into correct data directory"""
        
        #Data values
        self.data_transfer_complete = False
        self.transfer_prof_text = 'Data transfer'
        self.progress_val = 0
        self.PL_mid = None
        self.p_nan_points = None
        
        #Start data processing in a thread
        pr_thread = threading.Thread(target = self.post_recording_protocol)
        pr_thread.start()
        
        #Create a progress diaglog window 
        
        self.data_transfer = QtGui.QProgressDialog("Preparing to process data", "Cancel", self.progress_val, int(self.Record_Time.value() * 60.0), self)
        self.data_transfer.setWindowTitle("")
        self.data_transfer.setWindowModality(QtCore.Qt.WindowModal)
        self.data_transfer.setModal(True)    
        self.data_transfer.show()
        #self.data_transfer.activateWindow()
        QtGui.QApplication.processEvents() #Update the GUI 
               
        #Update the progress dialog untill everything has completed
        old_text = self.transfer_prof_text

        while not self.data_transfer_complete:
            #print(old_text, self.transfer_prof_text)
            if self.transfer_prof_text != old_text:

                print("running")
                self.data_transfer.setLabelText(self.transfer_prof_text)
                
                old_text = self.transfer_prof_text
          
            self.data_transfer.setLabelText("{}".format(self.transfer_prof_text))
            self.data_transfer.setValue(self.progress_val)
                
            
            QtGui.QApplication.processEvents() #Update the GUI        
 
        pr_thread.join()
        
        if self.ts_error:
            self.data_transfer.close()
            ts_msg = "There was a problem with the recording: One of the cameras dropped frames\nYou should rerun the recording. No data will be saved"
        
            ts_msgBox = QtGui.QMessageBox()
            ts_msgBox.setText(ts_msg)
            ts_msgBox.exec_()
            
            return 

        
        
        if self.PL_mid != None:
            
            self.feedback_gui(self.PL_mid)
        
        self.data_transfer.close() #Try to close the data transfer window later (may be faster?)
        self.start_button.setText("Start Recording") 
        self.show_window_1() #Go back to the demographics window
        

    def feedback_gui(self, PL = -999):
        """Open a dialog to give feedback on the participants score"""
        
        feedback_dialog = feedbackDialog(parent = self, PL = PL)
        feedback_dialog.exec_()
        
        print("Show a feedback GUI")

        
    def update_progress_value(self, val):
        """update the progress bar value (Note: Doesnt actually update the progress bar but is used to update it)"""
        self.progress_val = val
        
    
    def check_timestamp_error(self):
        """Check that the timestamps for the client and server are not more than 5 millisecond different at any point
            
            Return True if there are timing problems
            
            Return False otherwise
        """
        time_client = np.loadtxt("time_stamps.csv", delimiter = ',')
        time_server = np.loadtxt("timestamps_server.csv", delimiter = ',')
        
        time_client = time_client[:min(time_client.shape[0], time_server.shape[0])]
        
        time_server = time_server[:min(time_client.shape[0], time_server.shape[0])]
        time_client[time_client < 0] = np.NaN
        time_server[time_server < 0] = np.NaN
        
        if np.any(np.abs(time_client - time_server) > 5):
            
            return True
        else:
            return False
        
    def get_demographics(self):
        """Retrieve the demographics information"""
        
#        self.Forename_edit.text()        
#        self.Surname_edit.text()   
#        self.ID_edit.text()
#        self.DOB_edit.date()
        
        demographics = {'forename': self.Forename_edit.text(), 'surname': self.Surname_edit.text(), 
                        'DOB': self.DOB_edit.text(), 'ID': self.ID_edit.text(), 'Gender': self.Gender_edit.currentText(), 'Experiment': 'ExpOne', 
                        'condition': self.ConditionStack.currentWidget().currentText(), 'RecTime':  self.Record_Time.value()}

        return demographics
#        self.Gender_edit.setCurrentIndex(0)
#
#            
#        self.DOB_edit.Date)
                
                
    def archive_files(self):
        """Move the recorded files to the appropriate directory"""
        
       
        fos = FileOrderingSystem(self.storage_loc) #If self.storage_loc == None, it will save to the main directory. Else it will save to the selected location
        
        demographics = self.get_demographics()  
        
        fos.find_participant_dir(demographics) #Call this to check the participant directory exists. If not make one
        fos.find_participant_recording()
        fos.prep_record_directory()
        
        fos.move_files_to_record()
        
        pd.Series(demographics).to_csv(os.path.join(fos.recording_directory, 'demographics.csv'))
        
        return fos.recording_directory #Return the records directory
        

    def get_IR_data(self):
        """Request IR data is processed"""
        
        self.backend_camera.TCP_client_request_IRPoints()        



    ##---------------------------------------------##
	##---------------------------------------------##       
	##---------------Depreciated Functions---------##        
	##---------------------------------------------##        
	##---------------------------------------------##        
	##---------------------------------------------##
	##---------------------------------------------##
        
    def progressBar_update(self, t):
        """Depreciated"""
        self.ProgressBar.setMaximum(t)
        
        t0 = time.time()
        
        while True:
            
            timer = time.time() - t0

            self.ProgressBar.setValue(timer)
            
            if self.recording_Terminate:
                break #If recording terminate exit 
            
  
    def create_info_group(self):
        """Depreciated? Doesn't seem to do anything"""
        self.info_box = QtGui.QGroupBox("Info")
        
        info_grid = QtGui.QGridLayout()                
        
        Rec_loc = QtGui.QLabel('Rec Loc')
        
        info_grid.addWidget(Rec_loc, 0,0, 1,1)
        
        self.info_box.setLayout(info_grid)
        
        return info_grid
    
    def launch_server_pi(self):
        """DEPRECIATED:
            Try to start the server on the RPi            
            """
        self.shh_connection = shh_client()
        self.shh_connection_thread = threading.Thread(target = self.shh_connection.start_server)
        self.shh_connection_thread.start()
         
        
        
    def create_recording_group(self):
        """DEPRECIATED"""
        self.recording_box = QtGui.QGroupBox("Recording")         
        box_grid = QtGui.QGridLayout()
        
        Record_time_label = QtGui.QLabel('Record Time')
        Record_time = QtGui.QDoubleSpinBox()
        Record_time.setValue(10)
        Record_time.setMinimum(0.000001)
        
        #Start recording button
        Start = QtGui.QPushButton("Start Recording")
        
        #Progress bar
        progress = QtGui.QProgressBar(self)   
    
        box_grid.addWidget(Start,               0, 2, 1, 2)    
        box_grid.addWidget(Record_time_label,   0, 0, 1, 1)    
        box_grid.addWidget(Record_time,         0, 1, 1, 1)   
        box_grid.addWidget(progress,            1, 0, 1, 4)  
        
        box_grid.setSpacing(1) 
        self.recording_box.setLayout(box_grid)
        
        return self.recording_box

if __name__ == '__main__':
    
    multiprocessing.freeze_support() #Needed for the executable version of PSAT (made with PyInstaller)
    
    if not onDesktop:        
        multiprocessing.set_start_method("spawn") #Needs to be set else the multiprocessing in the camera_backend fails for some reason
        
    app = QtGui.QApplication(sys.argv)
#    app.autoSipEnabled() 
    ex = MainWindow() #Run the GUI
    
    #Set the style (colors etc of the GUI)
    ex.setStyleSheet("""QMainWindow {background: rgb(13,11,13)}
    
                        QGroupBox {background: rgb(52,50,52); border: 0px solid rgb(255,255,255); border-radius: 0px; margin-top: 0.5em;
                        font-family: embrima; font-size: 20px; font-weight: 500}
                        
                        
                        QGroupBox::title {color: 'white'; subcontrol-origin: margin; left: 4px; padding: 0 3px 0 3px;}
                        
                        QLabel {color: 'white'; font-family: embrima; font-size: 18px }       
                        
                        QDialog {background: rgb(52,50,52); border-radius: 0px; border: 0px solid rgb(16, 159, 221);}
                        
                        QLineEdit {background: rgb(52,50,52); color: rgb(255, 255, 255); font-weight: 800;
                        border: 1px solid rgb(16, 159, 221); font-family: embrima; font-size: 15px; padding: 3px;}    
                        
                        QLineEdit#MyTimeLineEdit {border: 1px solid rgb(221,89,2);}
                        
                        QCheckBox {color: rgb(255, 255, 255); font-weight: 800; font-family: embrima; font-size: 15px; padding: 3px;}  
                        
                        QCheckBox::indicator {width: 10px; height: 10px;border: 1px solid rgb(0,0,0); background-color: rgb(255,255,255)}
                        
                        QCheckBox::indicator:checked { background-color: rgb(221, 89, 2);}
                              
                        MyDateLineEdit {background: rgb(52,50,52); color: rgb(255, 255, 255); font-weight: 800;
                        border: 1px solid rgb(221, 89, 2); font-family: embrima; font-size: 15px; padding: 3px;}   
                        
                        QDateEdit {background: rgb(52,50,52); color: rgb(255, 255, 255); font-weight: 800;
                        border: 1px solid rgb(16, 159, 221); font-family: embrima; font-size: 15px; padding: 3px;}
                        
                                       
                        QDoubleSpinBox {background: rgb(0,0,0); color: 'white';}
                        
                        
                        QPushButton {background: rgb(221,89,2); color: 'white'; font-family: embrima; font-size: 20px; font-weight: 500;
                                     border-radius: 0px; border: 0px solid rgb(0,0,0); padding: 2px;}
                                     
                                     
                        QPushButton:pressed {background-color: rgb(255, 105, 0); border-style: inset;}
                        
                        
                        
                        
                        
                        QToolButton {border-radius: 5px}
                        
                        QComboBox {background: rgb(52,50,52); color: rgb(255, 255, 255); font-weight: 800; font-size: 15px;
                        border: 1px solid rgb(16, 159, 221); padding: 3px}
                        
                        QComboBox QListView {background-color:rgb(13,11,13);  border: 1px solid rgb(16, 159, 221);}   
                        
                        Icon_Button {background-color: rgb(52,50,52); border: 1px solid rgb(91, 204, 58); border-radius: 0px;} 
                        
                        Text_Button {background-color: rgb(52,50,52); color: rgb(255,255,255); border: 1px solid rgb(91, 204, 58); 
                                     border-radius: 0px; font-family: embrima; font-size: 17px; font-weight: 700} 
                       
                        QWidget#camera_checkbox {border: 1px solid rgb(221,89,2); }
                        QLabel#label {color: rgb(16, 159, 221);}
                        QLabel#labelClient {color: rgb(221, 89, 2);}
                        
                        QPushButton#controlButton {padding: 5px;}
                        positionLabel {background-color: rgb(16, 159, 221); font-size: 24px; font-weight: 800; }     
                        
                        QMenuBar {background-color: rgb(52,50,52); color: rgb(255,255,255)}
                        
                        QAction {background-color: rgb(52,50,52); color: rgb(255,255,255)}
                        
                        recordingLocLabel {background-color: rgb(52,50,52); font-size: 10px; padding: 5px}

                                         
                        """); #Change the background color
    if not onDesktop:
        ex.showFullScreen() #If on the raspberry Pi execute in full screen mode

    sys.exit(app.exec_())
