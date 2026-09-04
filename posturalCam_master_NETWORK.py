# -*- coding: utf-8 -*-
"""

"""

import sys
import time, io, os, glob, pickle, socket, threading, subprocess, multiprocessing, queue, pdb, itertools, struct

import psutil #To monitor memory

#import paramikomultiprocessing
try:
    import picamera #Import picamera if we are not on windows (fudge to check if on RPi's)
    from picamera.array import PiRGBArray
except ImportError:
    print("ImportError: No module named 'picamera'. If you are on a desktop this warning can be safely ignored")

import cv2
import matplotlib.pylab as plt
from scipy.signal import butter, filtfilt, freqz
from mpl_toolkits.mplot3d import Axes3D
import seaborn as sns
import pandas as pd
import numpy as np
from pykalman import KalmanFilter #For kalman filtering
from natsort import natsort

import network_utils as ntu
import ir_marker

if getattr(sys, 'frozen', False):
   base_path = sys._MEIPASS   
else:   
   base_path = os.path.dirname(os.path.realpath(sys.argv[0]))



#This next line may be important on the RPi? I can't remember why it is here
try:
    os.chdir(os.path.dirname(sys.argv[0])) #Switch to the directory that the file is in (Why are we doing this??)
except:
	pass

def splitfn(fn):
    path, fn = os.path.split(fn)
    name, ext = os.path.splitext(fn)
    return path, name, ext
    
def nothing(x):
    """A pass function for some openCV files"""    
    pass

class NN_PiVideoClient:
    """A Non-networked video client. Allow us to capture video in a thread and poll that video"""
    
    def __init__(self, sensor_mode = 0, framerate = None, resolution = None, resize = None):    
        
        
        self.camera = picamera.PiCamera(sensor_mode = sensor_mode, resolution = resolution, framerate = framerate)
#        self.camera.resolution = resolution
#        self.camera.framerate = framerate
#        self.camera.shutter_speed = 10000
        if resize == None:
            self.RawCapture = PiRGBArray(self.camera, size = resolution)  
        else:
            self.RawCapture = PiRGBArray(self.camera, size = resize) 
            
        self.stream = self.camera.capture_continuous(self.RawCapture, format = 'rgb', use_video_port = True, resize = resize)
        
        self.frame = None
        self.stopped = False
        
    def start(self):
        """Start getting frames on the thread"""
        threading.Thread(target = self.update, args = ()).start()
        
    def update(self):
        
        for f in self.stream:
            
            self.frame = f.array
            self.RawCapture.truncate(0)
            
            if self.stopped:
                
                self.stream.close()
                self.RawCapture.close()
                print("CAM CLOSE")
                self.camera.close()
                return 'DEAD'
                
    def read(self):
                
        return self.frame
        
    def stop(self):
        
        self.stopped = True
        
    
class PiVideoClient:
    """A object to recieve video from the surver and provide methods to access the most recent frame"""
    def __init__(self, sock):
        
        self.data = None
        # initialize the frame and the variable used to indicate
	  # if the thread should be stopped
        self.frame = None
        self.stopped = False
        
        self.connection = sock.makefile('rb') #Make the socket into a file like object       

        
    def start(self):
        """start the thread to read frames from the video stream"""
        self.preview_thread = threading.Thread(target=self.update, args=())
        
        
        self.preview_thread.start()
        
        return 
        
        
    def update(self):
        
        
        while True:
           
         
            image_len = struct.unpack('<L', self.connection.read(struct.calcsize('<L')))[0]
            
            if not image_len:
                self.stopped = True
        
            self.data = self.connection.read(image_len) #Read frame from the network stream
            
                    
            if self.stopped:                
                print("CLOSEIT")
                self.connection.close() #Close the file (test if it closes socket)
                
                
                return 

    def read(self):
        """Read and decode a frame"""
        
        if self.stopped:
            
            return "DEAD" #Return DEAD if the preview has finished
            
        if self.data != None:
            frame = np.fromstring(self.data, dtype=np.uint8) 
            
            image = cv2.imdecode(frame, 1)
            
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB) #Convert image to RGB
             
            return image
            
 
    def stop(self):
		# indicate that the thread should be stopped
        self.stopped = True
        
        
class tsOutput(object):
    """File object to save the video frames to. Also saves camera time stamps to disk"""
    def __init__(self, camera, video_filename, ts_filename):
        
        
        self.camera = camera
        self.video_output = open(video_filename, 'wb')
        self.ts_output = open(ts_filename, 'w')
        self.start_time = None
        
    def write(self, buf):
        """Write the buffer to file"""
        self.video_output.write(buf) #Write the buffer to the video_output stream
        
        if self.camera.frame.complete and self.camera.frame.timestamp:
            
            if self.start_time is None:
                self.start_time = self.camera.frame.timestamp
            self.ts_output.write("{}\n".format((self.camera.frame.timestamp - self.start_time) / 1000))
            
                
    def flush(self):

        self.video_output.flush()
        self.ts_output.flush()

    def close(self):
        self.video_output.close()
        self.ts_output.close()




class ts2Output(object):
    """Same as tsOutput but saves the timestamps to an array in memory. The array (tsarray) must be created before calling this function"""
    def __init__(self, camera, video_filename, ts_filename):
        
       
        self.camera = camera
        self.video_output = io.open(video_filename, 'wb')
        self.start_time = None
        self.i = 0
        
        #File subdirectories
        self.calibration_subdir = "calibration_images"
        self.video_file_subdir = "video_files"
        
    def write(self, buf):
        
        self.video_output.write(buf) #Write the buffer to the video_output stream
        
        if self.camera.frame.complete and self.camera.frame.timestamp:            
            
            tsarray[self.i] = self.camera.frame.timestamp
            
            self.i +=1 
            
                
    def flush(self):

        self.video_output.flush()


    def close(self):
        self.video_output.close()


class posturalCam:
    """Postural Camera instance"""

    def __init__(self, cam_no = 0, kind = 'None', sensor_mode = 6, resolution = (1280, 720), framerate = 60, vflip = False):
        """Initialise the postural cam.
        Args: 
        kind - Either 'client' or 'server' depending on the RPi
        sensor_mode - Leave at 6. See Picamera docs
        resolution - The camera resolution. This should not be changed
        framerate - Frame rate of the recording. 
        vflip - Boolean: Flip the image along the vertical axis"""
        
        self.cam_no = cam_no
        self.sensor_mode = sensor_mode
        self.resolution = resolution
        self.framerate = framerate
        self.vflip = vflip
        
        self.start_time_delta = 0.5 #Delay between each stage of camera recording sequence when networked
        
        
        self.host_addr = '192.168.0.3' #Server address
        
        
        #File subdirectories
        self.video_fname = None
        self.video_server_fname = None
        self.calibration_subdir = "calibration_images"
        self.video_file_subdir = "video_files"
    
    
    #------------------------------------------#
    #-------------Camera Methods---------------#
    #------------------------------------------#
    #------------------------------------------#
    #------------------------------------------#

    def init_camera(self):
        """Initialise the PiCamera

        This must be called before any recording can take place"""
        
        self.camera = picamera.PiCamera(sensor_mode = self.sensor_mode, resolution = self.resolution, framerate = self.framerate) 
        self.camera.vflip = self.vflip
        
#        self.camera.shutter_speed = 700
        
    def record_video(self, t, preview = True, v_fname = "temp_out.h264", v_format = "h264"):
        """record video for t seconds and save to file. Save a second file with the time stamps
        Optionally pass the name and format to save the file to.        
        """        
       
        if preview:
            self.camera.start_preview()
        
        try:
            self.camera.start_recording(tsOutput(self.camera, v_fname, "time_stamps.csv"), format = v_format, 
                                        level ="4.2")      
            
            self.camera.wait_recording(t)
#            print("SHUT SPEED: {}".format(self.camera.exposure_speed))
            self.camera.stop_recording()
        except:
            if preview:
                self.camera.stop_preview()
            raise IOError("Camera could not record")
            
        if preview:
            
            self.camera.stop_preview()

    def destroy_camera(self):
        """Close the PiCamera. Always call at the end of recording"""
        self.camera.close()



    #------------------------------------------#
    #-----------Server Side Methods------------#
    #------------------------------------------#
    #------------------------------------------#
    #------------------------------------------#


    def TCP_server_start(self):
        """A TCP server to manage the serverCam.

        When this is called a server will start on the server RPi and await instructions from the client RPi
        
        Wait for a connection from the client. 
        
        Note: After sending video the client will be disconnected. 
        
        Except the following commands from the client:
                'start_UDP': Start a UDP server to wait for recording commands
                #Check UDP server: Check UDP server is live
                'send_video': Request the latest recorded video
                'KILL': Kill the TCP connection. 
        """
        
        #Create a TCP socket
        serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #Create a socket object
    
        host = self.host_addr #Get local machine name
        port = 8888 #Choose a port
        
        print('TCP Server: starting on {} port {}'.format(host, port))
        
        #Bind to the port
        serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) #Allow the address to be used again
        serversocket.bind((host, port)) 
        
        #Queue up 1 request    
        serversocket.listen(1)      
            
        #Establist connection    
            
        while True:
            ##ACCEPT CONNECTIONS IN A CONTINUOUS LOOP.
            
            print("\nTCP Server: Waiting for New connection")
            self.clientsocket, addr = serversocket.accept()
            print("TCP Server: Connection established with {}".format(addr))
            
            self.server_live = True #The server is up
            
            while self.server_live:
                
#                data_len = struct.unpack('<L', self.clientsocket.recv(struct.calcsize('<L')))[0] #Recieve data specifying the message length
#                print(data_len)
#                print("TCP Server: Waiting for data (Instruction)")
#                data = self.clientsocket.recv(data_len) #Recive data_len bytes
                print("\nTCP Server: waiting for instruction")
                data = ntu.recv_msg(self.clientsocket)
                
                #Check for data. If not the connection has probably gone down
                if not data:
                    print("TCP Server: Something went wrong with the connection. Please reconnect")
                    self.server_live = False
                    
                
                try:
                    data_decoded = data.decode()
                except AttributeError:
                    print("Could not decode data. This probably means the client has shutdown the TCP connection")
                    print("Closing the connection")                    
                    self.clientsocket.close()
                    self.server_live = False                    
                    break
                
                print("TCP Server: {} Bytes recived from {}: {}".format(len(data), addr, data_decoded))
                
                if data_decoded == 'start_camPreview':
                    
                    self.TCP_server_send_camPreview() 
                    
               
                elif data_decoded == 'start_UDP':
                    
                    self.UDP_server_start() #Start a UDP server and wait for recording instructions
                    #We will now wait here until UDP server closes, hopefully with a video recorded
               
                elif data_decoded == 'send_video':   
        
                    self.TCP_server_send_video()    
                      
                elif data_decoded == 'send_timestamps':

                    self.TCP_server_send_timestamps()
    
                    
                elif (data_decoded == 'send_IRPoints:serial') or (data_decoded == 'send_IRPoints:parallel'):

                    if ':parallel' in data_decoded:
                        
                        self.TCP_server_send_IRPoints(parallel = True)        
                    
                    else:
                    
                        self.TCP_server_send_IRPoints(parallel = False)  
                        
                elif data_decoded == 'shutdown':
                    
                    self.clientsocket.close()#Shutdown the server
                    self.server_live = False
                    return #Exit the loop
                          
                elif data_decoded == 'KILL':  #Kill the connection              
                    
                    self.clientsocket.close()
                    self.server_live = False
                    print("TCP Server: TCP connection closed")
                    
                else:
                    print("TCP Server: Message not recognised: {}".format(data_decoded))                   
    
    def TCP_server_shutdown_routine(self):
        """Close down the raspberry pi. """
        
        ##Run checks to make sure we can shutdown
        
#        subprocess.call(["sudo", 'shutdown', 'now'])
        pass
        
    
    def TCP_server_send_camPreview(self):
        """Create a camPreview server and stream images to it via a thread to allow the server to still recieve messages
        Send a continuous stream of images over TCP connection"""
        
        print("TCP Server: Starting Cam Preview")
        #Create a TCP socket
        camPreview_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #Create a socket object
    
        host = self.host_addr #Get local machine name
        port = 9999 #Choose a port for the camera preview
        
        print('TCP Server: starting cam server connection on {} port {}'.format(host, port))
        
        #Bind to the port
        camPreview_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) #Allow the address to be used again
        camPreview_socket.bind((host, port)) 
        
        #Queue up 1 request    
        camPreview_socket.listen(1)     
        
        clientsocket, addr = camPreview_socket.accept() #Accept a connection
        connection = clientsocket.makefile('wb') #Make a file like object out of the socket
        
        ##Create the camera
        
        self.init_camera()
        self.camera.framerate = 30  #Change the framerate to 30fps
#        self.camera.resolution = (640, 480)              
        
        start = time.time()
        stream = io.BytesIO()
        
        t0 = time.time()
        
        for foo in self.camera.capture_continuous(stream, 'jpeg', use_video_port = True, resize =  (640, 368)):
            
            try:            
                connection.write(struct.pack('<L', stream.tell()))
                connection.flush()
                
                # Rewind the stream and send the image data over the wire
                stream.seek(0)
                
                dat = stream.read()
              
                connection.write(dat)
               
                # Reset the stream for the next capture
                stream.seek(0)
                stream.truncate()
                t1 = time.time()
                print("Time: {} Memory: {}".format(1/(t1-t0), psutil.virtual_memory()[2]))
                t0 = t1
                
            except:
                
                print("Send CamPreview Error: ", sys.exc_info())                
                
                break    
            
        self.destroy_camera() #Destroy the camera ready for the next command
        



    def TCP_server_send_video(self):               
        """Server method: Send a video file over a TCP stream to the client"""
     
        f_vid = open('server_video.h264', 'rb') #Open file to send
        print("TCP Server: Sending video file")

        while True:
               
            l = f_vid.read(1024) #Read video data
            
            if not l:

                break 
                      
            ntu.send_msg(self.clientsocket, l)
            
        ntu.send_msg(self.clientsocket, 'END'.encode()) #Signal end of file transfer
        print("TCP server: Sending Video complete")
 
    def TCP_server_send_timestamps(self):                    
        """Server method: Send time stamp data over a TCP connection to the client"""           
        print("TCP Server: Sending time stamps")
        
        time_stamps = open("time_stamps.csv", 'rb')

        while True:
            
            l = time_stamps.read(1024)
            
            ntu.send_msg(self.clientsocket, l)
            
            if not l:
                ntu.send_msg(self.clientsocket, 'END'.encode())          
                break            
            
        print("TCP Server: Sending time stamps complete")
        time_stamps.close()

    def TCP_server_send_IRPoints(self, parallel):
        """Server method: Send IR points over a TCP connection to the client"""           

        print("TCP Server: Processing IRPoints")
        
        #GET THE IR DATA POINTS. THEN SEND THEM 
        self.proc = posturalProc(v_fname='server_video.h264', kind='server')
    #                    markers = self.proc.get_ir_markers_parallel() #Get the markers in parallel
        
        #If parellel flag then use multiple cores to process the output
        if parallel:
            markers = self.proc.get_ir_markers_parallel()
        
        else:
            markers = self.proc.get_ir_markers() #Get the markers in 
            
        print("TCP Server: Processing IRPoints finished \n TCP Server: Sending IRPoints")    
        #Send the marker data
        marker_bytes = pickle.dumps(markers) #Get bytes object of markers NOTE: This may be better as a numpy serialised object
        
        ntu.send_msg(self.clientsocket, marker_bytes)

             
    def UDP_server_start(self):
        """Postural cam server.
         It will wait for a message telling it to initialise the camera. Then wait for another telling it to start recording.

        This method will then execute the recording as per the UDP clients instructions"""
        
        # Create a UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Bind the socket to the port
        
        host, port = '192.168.0.3', 9999        
        server_address = (host, port) #The server's address
        print('UDP Server: starting server up on {} port {}'.format(server_address[0], server_address[1])) 
        
        sock.bind(server_address)       
            
        print('UDP Server: waiting for data')
        data, address = sock.recvfrom(1024)        
        server_init_time = time.time() #Time server recieved time message
        
        
        data_decoded = data.decode()     
        print('UDP Server: {} bytes recieved from {}: {}'.format(len(data), address, data_decoded)) 
        data_decoded = data_decoded.split(',') #Split the message into components. The first is the time on the client. The second is the time to record for.
        
        #THe decoded message is a string with two sections (comma seperated). The first indicates the time on the client. The second indicates the required recording time
        print("UDP Server: Recording video for {} seconds".format(data_decoded[1]))
        while True:
            
            if time.time() >= server_init_time + self.start_time_delta:
            
                self.init_camera()
#                time.sleep(1)
                self.record_video(float(data_decoded[1]), v_fname = 'server_video.h264')
                self.destroy_camera()
                print("UDP Server: Recording video finished")
                
                break
        

        if data:
            message = 'recordingSuccess' #Signal that everything worked.
            sent = sock.sendto(message.encode(), address)
            print('UDP Server: sent {} bytes message back to {}: {}'.format(sent, address, message))
    
                 
    
    #------------------------------------------#
    #-----------Client Side Methods------------#
    #------------------------------------------#
    #------------------------------------------#
    #------------------------------------------#
     
    def TCP_client_start(self):
        """Start a TCP Client up.
        When done call self.TCP_client_close()"""
        print("") #Print a blank line
        self.TCP_client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
        host = self.host_addr
        port = 8888
        
        connection_made = False
        #Try to make connection 100 times
        i = 0
        
        try:    
            self.TCP_client_socket.connect((host, port))
            connection_made = True
            print("TCP Client: Connected to {} on port {}".format(host, port))   
        except (ConnectionRefusedError, TimeoutError) as exp:
            print("TCP Client: Could not connect to server. Trying again in 0.5 seconds")
            i += 0
            if i > 100:
                print("TCP Client: Failed to conned 100 times")                    
                raise ConnectionRefusedError               
             
        return connection_made
    
    def TCP_client_shutdown_server(self):
        """Request for the server to shut itself down"""
        
        ntu.send_msg(self.TCP_client_socket, "shutdown".encode())
        
        
    def TCP_client_request_videoPreview(self):
        """Request a video preview from the server picamera. Uses a thread to poll the frames. Currently waits until all recording has finished"""
        
        ntu.send_msg(self.TCP_client_socket, 'start_camPreview'.encode()) #Request video 
        
    
       
        self.camPreview_client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
        host = self.host_addr
        port = 9999
        
        #Try to make connection 100 times
        i = 0
        while True:
            try:    
                self.camPreview_client_socket.connect((host, port))
                break
            except ConnectionRefusedError as exp:
                print("CamPreview connection could not be made. Trying again in 0.5 seconds")
                i += 0
                if i > 20:
                    print("TCP Client: Failed to conned 100 times")
                    raise ConnectionRefusedError 
                
                time.sleep(0.1)
                
        print("TCP Client: Connected to {} on port {}".format(host, port))  
        
        self.preview_client = PiVideoClient(self.camPreview_client_socket)        
        self.preview_client.start()
    
    def TCP_client_poll_videoPreview(self):
        """Get the latest frame from the PiCamera on the server"""
        return self.preview_client.read()
        
    def TCP_client_stop_videoPreview(self):
        """Close the server video preview and server"""
        
        self.preview_client.stop()
        self.camPreview_client_socket.close()   
     
        print("CLOSED SOCKET")

    def TCP_client_request_video(self):
        """Request and recieve the last video from the TCP server. 
        
        Note: Always request the video last! It closes the connection. If you dont want this to happen you will need to reprogram to send information about how big the video file is and then send a end transfer command"""
        
        print("TCP Client: Requesting video from server")

        message = 'send_video'.encode() #message to TCP server
        
#        self.TCP_client_socket.send(struct.pack('<L', len(message))) #Send the length of the message to recieve        
#        self.TCP_client_socket.send(message) #Request video 
        ntu.send_msg(self.TCP_client_socket, message)
        
        ##Open the video file and wait to recieve the video        
        f_video_recv = open(self.video_server_fname, 'wb') #Fails if video recording hasn't occured on same connection first
        
        print("TCP Client: Recieving data")        
      
        
        while True:
            
#            data_len = struct.unpack('<L', self.TCP_client_socket.recv(struct.calcsize('<L')))[0] #Recieve data specifying the message length
            
            data = ntu.recv_msg(self.TCP_client_socket)  
            
            if data == 'END'.encode():
                
                break            
            
#            data = self.TCP_client_socket.recv(data_len) #Recieve data of len data_len
            else:
                f_video_recv.write(data)    
        
        f_video_recv.close() #Close the video file
            
        print("TCP Client: Video Recieved")        
    
    def TCP_client_request_timestamps(self):
        """Request time stamps. Optionally pass a callback function"""
        
        print("TCP Client: Requesting timestamps from server")
        
        ntu.send_msg(self.TCP_client_socket, 'send_timestamps'.encode())
#        self.TCP_client_socket.send("send_timestamps".encode())         
        
#        time_stamps_recv = open("time_stamps_server.csv", 'wb')
        time_stamps_bytes = b'' #Buffer for data
        print("TCP Client: Recieving data")
        
       
        
        while True:
            
            data = ntu.recv_msg(self.TCP_client_socket)
            
            if data == 'END'.encode():
                break
            
            else:

                time_stamps_bytes += data 
        
                
        time_stamps_f = open("timestamps_server.csv", 'wb')
        
        
        time_stamps_f.write(time_stamps_bytes)
        
        time_stamps_f.close() #Close timestamps file

        
    def TCP_client_request_IRPoints(self, callback_function = None, *callback_args):
        """Request an IR points file from the server and get IR points from the client. The server will analyse the points data and then pass it to here
        
        Notes: May want to do this as a thread else it will block processing on the client"""
        
        #Start client processing
        
        self.video_fname = 'testIR.h264'
        self.proc = posturalProc(v_fname=self.video_fname, kind='client') 
        
        
        q = queue.Queue(1) #Queue to place the results into
        IR_Thread = threading.Thread(target = self.proc.get_ir_markers_parallel, kwargs = {'out_queue': q, 'callback_function': callback_function})   
#        IR_Thread = threading.Thread(target = self.proc.get_ir_markers, kwargs = {'out_queue': q})          
        IR_Thread.start() #Start the marker thread
        
        ###Get server data   
#        
        print("TCP Client: Requesting IR Points data")
        ntu.send_msg(self.TCP_client_socket, 'send_IRPoints:parallel'.encode())
        

        IR_points_bytes = ntu.recv_msg(self.TCP_client_socket)      
        self.IR_points_server = pickle.loads(IR_points_bytes)
        print("TCP Client: IR Points Data recieved")
        
        
        ir_points_out = q.get()
        
        if IR_Thread.is_alive():
            
            IR_Thread.join() #Wait for IR Thread to finish
            
       
        return ir_points_out, self.IR_points_server        
      
    
    def TCP_client_close(self):
        """Close the TCP client socket"""
        
        print("TCP Client: Closing connection to server")
        
        ntu.send_msg(self.TCP_client_socket, 'KILL'.encode())
        self.TCP_client_socket.close()


    def TCP_client_start_UDP(self, t, video_fname):
        """Tell the server to start the UDP server. Wait 0.25 seconds. Then tell the server to record a video of t seconds
        t: The number of seconds the camera will record for
        video_fname: The name of the file to record to. The server video will have _server appended to it.
        """
        
        
        self.video_fname = video_fname #The name of the last video recorded
        split_name = self.video_fname.split('.')
        self.video_server_fname = '{}_server.{}'.format(split_name[0], split_name[1])


        message = 'start_UDP'.encode() 
#        self.TCP_client_socket.send(struct.pack('<L', len(message))) #Send the length of the message to recieve           
#        self.TCP_client_socket.send(message)

        ntu.send_msg(self.TCP_client_socket, message)
        
        time.sleep(0.25) #IGive UDP server time to launch
        
        self.UDP_client_start(t)     

    def UDP_client_start(self, t):
        """Start client side UDP server.
         
        """
        
        client_recordingThread_ready = threading.Event() #An event to say the client recording thread is ready
        client_recording_ready = threading.Event() #An event to tell the thread to initiate recording
        
        
        recording_Thread = threading.Thread(target = self.UDP_client_record, args = (t, client_recordingThread_ready, client_recording_ready,))        
        recording_Thread.start() #Start recording Thread. May have constructer overhead

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        host, port = '192.168.0.3', 9999        
        server_address = (host, port) #The server's address
        
        print('UDP Client: Sending message to UDP Server {} on port {}'.format(host, port))       
        
        client_recordingThread_ready.wait() #Wait until the recording thread is ready
        
        
        #Tell server to start recording proceedure
        self.start_time = time.time()           
        client_recording_ready.set() #Tell the thread to start recording
        sent = sock.sendto('{},{}'.format(self.start_time, t).encode(), server_address) #Send the current time and t)
        
        
        print("UDP Client: Recording video for {} seconds".format(t))
        
        
        print("UDP Client: Waiting on server response")
       
        data, server = sock.recvfrom(1024) #Wait for a response
        
        if data.decode() == 'recordingSuccess':        
        
            print('UDP Client: Message from UDP Server: {}'.format(data.decode())) #Decode data and print it
        
            print('UDP Client: Closing UDP socket')
            sock.close()
            
            recording_Thread.join() #Wait for recording on Client to end
            print("UDP Client: Recording video finished")
            
        else:
            raise IOError("UDP transfer failed")

    def UDP_client_record(self, t, client_recordingThread_ready, client_recording_ready):
        
        client_recordingThread_ready.set() #Signal that the tread is ready to start recording
        
        client_recording_ready.wait() #Wait until told to start
        
        init_time = self.start_time + self.start_time_delta + 0  #Minus a constant to try and get rid of asynchrony in cameras
        
        while True:
            
            if time.time() >= init_time:
                             
                self.init_camera()
            
            
#                time.sleep(1)        
                self.record_video(t, preview = True, v_fname = self.video_fname)   
                self.destroy_camera()
                print('UDP Client: Recording finished')
                break   
                  
        

    #------------------------------------------#
    #---------Server side video preview--------#
    #------------------------------------------#
    #------------------------------------------#
    #------------------------------------------#

    def videoPreview(self):
        """Preview video on this RPi"""        
        
        self.previewVid = NN_PiVideoClient(sensor_mode = 6, framerate = 30, resolution = (1280, 720), resize = (640, 368))
        self.previewVid.start()
        
    def poll_videoPreview(self):
        
        return self.previewVid.read()
        
    def stop_videoPreview(self):
        
        self.previewVid.stop()
        

        
    
                      
           
    
    
    


















        
class posturalProc:
    """Play back video from the PiCamera with OpenCV and process the video files"""
    
    def __init__(self, cam_no= 0, v_format = 'h264', v_fname = "temp_out.h264", calibration_dir = None, kind = 'client'):        
        """Initialise the processing object. Pass the format and name of the video file to be analysed, along with an optional location for the calibration files"""
        
        self.cam_no = cam_no        
        self.v_format = v_format
        self.v_fname = v_fname
        self.v_loaded = False
        
        self.kind = kind
        self.resolution = (1280, 720)
        
        
        ##If possible load the latest calibration parameters
        if self.kind == 'client':
            calib_fname = 'client_camera_calib_params.pkl'
        elif self.kind == 'server':
            calib_fname = 'server_camera_calib_params.pkl'
        
        #Or load the calibration for the preview cameras (which are a different resolution)             
        elif self.kind == 'client_preview':
            calib_fname = 'client_preview_camera_calib_params.pkl'
        elif self.kind == 'server_preview':
            calib_fname = 'server_preview_camera_calib_params.pkl'

            
        if calibration_dir != None:            
            calib_fname = os.path.join(calibration_dir, calib_fname)
        else:
            calib_fname = os.path.join(base_path, 'calibration', calib_fname)
            
        try:
            with open(calib_fname, 'rb') as f:
                if sys.version_info[0] == 2:
                    self.calib_params = pickle.load(f) #Pickle is different in python 3 vs 2
                else:
                    self.calib_params = pickle.load(f, encoding = "Latin-1") #Load the calib parameters. [ret, mtx, dist, rvecs, tvecs]     
                self.rms, self.camera_matrix, self.dist_coefs, self.rvecs, self.tvecs = self.calib_params
                print('{}: Initialisation: Camera calibration parameters were found'.format(self.kind))
        except:            
            print("{}:Initialisation: No camera calibration parameters were found".format(self.kind))
            
        
    def load_video(self):
        """Load the video. The video filename was specified on initialisation"""
        
        if self.v_loaded == False:
            print("Loading video file: {}".format(self.v_fname))
           
            if self.v_fname in glob.glob('*.h264'):
                print("FILE EXISTS")
            self.cap = cv2.VideoCapture(self.v_fname)
#            pdb.set_trace()
            if self.cap.isOpened() != True:                
        
                raise IOError("Video could not be loaded. Check file exists")
            
            
            self.v_loaded = True
            print("Video Loading: Video Loaded from file: {}".format(self.v_fname))
            
        else:
            print("Video Loading: Video already loaded")
    
        
    def play_video(self, omx = True):
        """Play back the video. If omx == True and we are on the raspberry Pi it will play the video via the omxplayer"""
        
       
        if os.name != 'nt':
            RPi = True
        else:
            Rpi = False
            
        if not (Rpi and omx):
            self.load_video()
            cv2.namedWindow("video", cv2.WINDOW_AUTOSIZE)
            
            
            while True:
                
                ret, frame = self.cap.read()
                
                if ret == False:
                    #If we are at the end of the video reload it and start again. 
                    self.v_loaded = False
                    self.cap.release() #Release the capture. 
                    self.load_video()
                    continue  #Skip to next iteration of while loop
                
                cv2.imshow("video", frame)
                
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
                
            
            self.cap.release()
            cv2.waitKey(1)
            cv2.destroyAllWindows()
            cv2.waitKey(1)
            self.v_loaded = False
        
        elif Rpi:
            subprocess.call(['omx', self.v_fname]) #Call omx player
    
    def average_background(self):
        """Not working"""
        
        self.load_video()
        
        
        ret, frame = self.cap.read()
        avg1 = np.float32(frame)
        i = 0
        while True:
            print(i)
            i +=1
            ret, frame = self.cap.read()
            
            if ret == False:
                #If we are at the end of the video reload it and start again. 
                break
            
            cv2.accumulateWeighted(frame, avg1, 0.05)
            res1 = cv2.convertScaleAbs(avg1)       
            
            
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
            
        
        plt.imshow(res1)
        
        self.cap.release()
        cv2.waitKey(1)
        cv2.destroyAllWindows()
        cv2.waitKey(1)
        self.v_loaded = False
        
    def background_MOG(self):
        """Not working"""
        self.load_video()
        
        fgbg = cv2.createBackgroundSubtractorMOG2()
        
        
        while True:
           
            ret, frame = self.cap.read()
            
            if ret == False:
                #If we are at the end of the video reload it and start again. 
                break
            
            fgmask = fgbg.apply(frame)           
            
            thresh = cv2.threshold(fgmask, 2, 255, cv2.THRESH_BINARY)[1]
            
#            frame[thresh == 0] = [0,0,0]
#            plt.plot(fgmask.flatten())
#            plt.show()
#            pdb.set_trace()
            
            cv2.imshow("fgmask", fgmask)
            cv2.imshow("thresh", thresh)
            
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
            
    
    def check_v_framerate(self, f_name = "points.csv", ax = None):
        """Plot the camera framerate. Optionally pass the framerate file name"""
        
        frame_data = pd.read_csv(f_name)     
        
        fps = 1000 / frame_data.diff()
       
        print(fps['0.0'].mean(), fps['0.0'].std())
        

        plt.plot(fps)
        plt.show()    

    
    def get_calibration_frames(self):
        """Allows us to choose images for calibrating the RPi Camera. The more the merrier (get lots of images from different angles"""
        
        i = 0
#        Check for previous files
        master_dir = os.getcwd()
        
        if not os.path.exists(os.path.join(master_dir, 'calibration', self.kind)):
            os.makedirs(os.path.join(master_dir, 'calibration', self.kind))
#        os.chdir(os.path.join(master_dir, "calibration", self.kind)) #Go to the calibration images directory
        file_list = glob.glob(os.path.join(master_dir, 'calibration', self.kind, '*.tiff'))
        output_list = glob.glob(os.path.join(master_dir, 'calibration', self.kind, 'output','*'))
        
 
        if file_list != []:
            
            cont = input("Calibration images exist. Press 'c' to overwrite or 'a' to append. Any other key to cancel ")
            
            if cont.lower() == 'c':
                
                for f in file_list:
                    os.remove(f)
                
                for f2 in output_list:
         
                    os.remove(f2)
                
                    
            elif cont.lower() == 'a':
                
             
                last_num = natsort.humansorted(file_list)[-1].split('.tiff')[0].split("_")[-1] #Gets the last image number
                last_num = int(last_num)
                
                i = last_num + 1
                    
            else:
                print("Escaping calibration")
                return 
        
#        os.chdir(master_dir)
        
        
        print("Camera Calibration: Loading Video")
        self.load_video() #Make sure the calibration video is loaded      
        
                 
        
        ret, frame = self.cap.read()
            
        
        while True:
                                    
            
            if ret == False:
                print("Camera Calibration: No more Frames")
                self.cap.release()
                cv2.destroyAllWindows()
                self.v_loaded = False
                break
            
            cv2.imshow("Calibration", frame)
            
            key_press = cv2.waitKey(1) & 0xFF
            
            if key_press == ord("n"):
                
                ret, frame = self.cap.read()
                continue
           
            elif key_press == ord("s"):      
                
                cv2.imwrite(os.path.join(os.getcwd(), 'calibration', self.kind, 'calib_img_{}.tiff'.format(i)), frame)
#                np.save(os.path.join(os.getcwd(), 'calibration', 'calib_img_{}'.format(i)), frame)
                i += 1
                ret, frame = self.cap.read()
               
                continue
            
            elif key_press == ord("q"):
                self.cap.release()
                cv2.destroyAllWindows()
                cv2.waitKey(1)
                self.v_loaded = False     
                break
            
                
                

    def camera_calibration(self):
        """Use the camera calibration images to try and calibrate the camera"""
        
        
        #Find all the images
        
        master_dir = os.getcwd()
        
        os.chdir(os.path.join(master_dir, "calibration", self.kind)) #Go to the calibration images directory
        
        debug_dir = 'output'
        if not os.path.isdir(debug_dir):
            os.mkdir(debug_dir)
        
  
        img_names = glob.glob("*tiff")
        
        if len(img_names) == 0:
            img_names = glob.glob("*jpeg")
        
        square_size = float(37.5) #New larger calibration object

        pattern_size = (9, 6)
        pattern_points = np.zeros((np.prod(pattern_size), 3), np.float32)
        pattern_points[:, :2] = np.indices(pattern_size).T.reshape(-1, 2)
        pattern_points *= square_size
        
        self.obj_points = []
        self.img_points = []
        h, w = 0, 0
        img_names_undistort = []
        for fn in img_names:
            print('processing %s... ' % fn, end='')
            img = cv2.imread(fn, 0)
            if img is None:
                print("Failed to load", fn)
                continue
    
            h, w = img.shape[:2]
            found, corners = cv2.findChessboardCorners(img, pattern_size)
            if found:
                term = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_COUNT, 30, 0.1)
                cv2.cornerSubPix(img, corners, (5, 5), (-1, -1), term)
    
            if debug_dir:
                vis = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
                cv2.drawChessboardCorners(vis, pattern_size, corners, found)
                path, name, ext = splitfn(fn)
               
                outfile = os.path.join(debug_dir,name+'_chess.png')
                cv2.imwrite(outfile, vis)
                if found:
                    img_names_undistort.append(outfile)
    
            if not found:
                print('chessboard not found')
                continue
    
            self.img_points.append(corners.reshape(-1, 2))        
            self.obj_points.append(pattern_points)
    
            print('ok')
    
        # calculate camera distortion
        self.rms, self.camera_matrix, self.dist_coefs, self.rvecs, self.tvecs = cv2.calibrateCamera(self.obj_points, self.img_points, (w, h), None, None)
    
        print("\nRMS:", self.rms)
        print("camera matrix:\n", self.camera_matrix)
        print("distortion coefficients: ", self.dist_coefs.ravel())
        
        
        ##Save distortion parameters to file
        if self.kind == 'server':
            fname = 'server_camera_calib_params.pkl'
            
        elif self.kind == 'client':
            fname = 'client_camera_calib_params.pkl'
            
        calib_params = self.rms, self.camera_matrix, self.dist_coefs, self.rvecs, self.tvecs
        
        if self.kind == 'server':
            fname = os.path.join(os.path.dirname(os.getcwd()), 'server_camera_calib_params.pkl')
            
        elif self.kind == 'client':
            fname =  os.path.join(os.path.dirname(os.getcwd()),'client_camera_calib_params.pkl')
            
        elif self.kind == 'server_preview':
            fname = os.path.join(os.path.dirname(os.getcwd()), 'server_preview_camera_calib_params.pkl')
        
        elif self.kind == 'client_preview':
            fname = os.path.join(os.path.dirname(os.getcwd()), 'client_preview_camera_calib_params.pkl')
            
            
        with open(fname, 'wb') as f:
            pickle.dump(calib_params, f)        #THIS MAY BE BETTER AS A TEXT FILE. NO IDEA IF THIS WILL LOAD ON THE RASPBERRY PI BECAUSE IT IS A BINARY FILE
        
        # undistort the image with the calibration
        print('')
        for img_found in img_names_undistort:
           
            img = cv2.imread(img_found)
        
            h,  w = img.shape[:2]
            newcameramtx, roi = cv2.getOptimalNewCameraMatrix(self.camera_matrix, self.dist_coefs, (w, h), 1, (w, h))
    
            dst = cv2.undistort(img, self.camera_matrix, self.dist_coefs, None, newcameramtx)
    
            # crop and save the image
#            x, y, w, h = roi
#            dst = dst[y:y+h, x:x+w]
            outfile = img_found.split(".png")[0] + '_undistorted.png'
            print('Undistorted image written to: %s' % outfile)
            cv2.imwrite(outfile, dst)
    
        cv2.destroyAllWindows()
        
        os.chdir(master_dir)
       
            

        
    def camera_calibration2(self):
        """DEPRECIATED
        Run after self.camera_calibration. This does the actual optimisizing and saves the parameters to file"""
        
        master_dir = os.getcwd()
        os.chdir(os.path.join(master_dir, "calibration")) #Go to the calibration images directory
        ##Run the calibration
        mtx = np.array([[400, 0, self.resolution[0]/2],
                        [0, 400, self.resolution[1]/2],
                        [0,0,1]])
        print(mtx)                
        print("Camera Calibration: Calibrating Camera. Please wait... This may take several minutes or longer")
        self.calib_params = cv2.calibrateCamera(self.objpoints, self.imgpoints, self.resolution, mtx, None, 
                                                flags =  cv2.CALIB_ZERO_TANGENT_DIST)
        
        
        print(self.calib_params[1])
#        self.calib_params = cv2.calibrateCamera(self.objpoints, self.imgpoints, self.resolution, proc.calib_params[1], proc.calib_params[2], 
#                                                flags = cv2.CALIB_USE_INTRINSIC_GUESS | cv2.CALIB_ZERO_TANGENT_DIST)

        self.calib_params = cv2.calibrateCamera(self.objpoints, self.imgpoints, self.resolution, self.calib_params[1], self.calib_params[2], 
                                                flags = cv2.CALIB_USE_INTRINSIC_GUESS)                                   

     
        
        print("Reprojection Error: {}".format(self.calib_params[0]))
        self.calib_params = list(self.calib_params)
        
        self.calib_params.append(self.objpoints)
        self.calib_params.append(self.imgpoints)
        self.ret, self.mtx, self.dist, self.rvecs, self.tvecs, self.objpoints, self.imgpoints = self.calib_params
        print("Camera Calibration: Calibration complete")
        
        if self.kind == 'server':
            fname = 'server_camera_calib_params.pkl'
            
        elif self.kind == 'client':
            fname = 'client_camera_calib_params.pkl'
            
        with open(fname, 'wb') as f:
            pickle.dump(self.calib_params, f)
            
        os.chdir(master_dir) #Set directory back to master directory. 
    
    
    def camera_calibration_circle(self):
        """DEPRECIATED
        Use the camera calibration images to try and calibrate the camera"""
        
        #termination criteria
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001) 

        #Prepare object points, like (0,0,0), (1,0,0)... (8,5,0)
        
        squares = (11,4)     
        
#        ##Square number format
        self.objp = np.zeros((np.prod(squares), 3), np.float32)
        objp[:,:2] = np.mgrid[0:squares[0], 0:squares[1]].T.reshape(-1,2)
#        
        #mm format
        square_size = 24.5 #mm
                
#        objp = np.zeros((np.prod(squares), 3), np.float32)
        
#        p = itertools.product(np.arange(0,square_size*squares[0],square_size), np.arange(0,square_size*squares[1],square_size))
#        objp[:,:2] = np.array([i for i in p])[:,::-1]
            
        #Arrays to store object points and image points for all the images
        self.objpoints = [] #3d points in real world space
        self.imgpoints = [] #2d points in image plane
        
        master_dir = os.getcwd()
        os.chdir(os.path.join(master_dir, "calibration")) #Go to the calibration images directory
        
        images = glob.glob("*npy")
        
        len_images = len(images)
        i = 0
        for fname in images:
            
            img = np.load(fname)
            
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
#            gray
#            plt.imshow(gray, cmap = 'gray')
#            plt.show()
#            pdb.set_trace()
            ret, corners = cv2.findCirclesGrid(gray, squares, None, cv2.CALIB_CB_ASYMMETRIC_GRID)
            
            if ret == True:                
                print("Camera Calibration: Processing Image: {} of {}".format(i, len_images))    
                self.objpoints.append(objp)                
#                cv2.cornerSubPix(gray, corners, (11,11), (-1,-1), criteria)
                
                self.imgpoints.append(corners)
                
                cv2.drawChessboardCorners(img, squares, corners, ret)
                cv2.imshow("img", img)
                cv2.waitKey(250)
            
            
            i += 1        
        cv2.destroyAllWindows()
        cv2.waitKey(1)
#        pdb.set_trace()    
        ##Run the calibration
        
#        print("Camera Calibration: Calibrating Camera. Please wait... This may take several minutes or longer")
#        self.calib_params = cv2.calibrateCamera(objpoints, imgpoints, gray.shape[::-1], None, None)
#        print("Reprojection Error: {}".format(self.calib_params[0]))
#        self.calib_params = list(self.calib_params)
#        self.calib_params.append(objpoints)
#        self.calib_params.append(imgpoints)
#        print("Camera Calibration: Calibration complete")
#        
#        if self.kind == 'server':
#            fname = 'server_camera_calib_params.pkl'
#            
#        elif self.kind == 'client':
#            fname = 'client_camera_calib_params.pkl'
#            
#        with open(fname, 'wb') as f:
#            pickle.dump(self.calib_params, f)
#            
#        os.chdir(master_dir) #Set directory back to master directory. 
        
        
    def check_camera_calibration(self):
        """DEPRECIATED
        Check the reprojection error"""
        
        tot_error = 0
        
        for i in range(len(self.objpoints)):
            
            imgpoints2, _ = cv2.projectPoints(self.objpoints[i], self.rvecs[i], self.tvecs[i], self.mtx, self.dist)
            error = cv2.norm(self.imgpoints[i], imgpoints2, cv2.NORM_L2) / len(imgpoints2)
            tot_error += error
        
        print("Check Camera Calibration: Total Error: {}".format(tot_error/len(self.objpoints)))
    
    
    def undistort(self, img):
        """undistort an image"""
        h,w = img.shape[:2]
        
        newcameramtx, roi = cv2.getOptimalNewCameraMatrix(self.mtx, self.dist, (w,h), 1, (w,h))
        
      
        dst = cv2.undistort(img, self.mtx, self.dist, None, newcameramtx)
        
        return dst
        
    def undistort_points(self, p):
       """Undistort points p where p is a 1XNx2 array or an NX1X2 array""" 
       
       dst = cv2.undistortPoints(p, self.camera_matrix, self.dist_coefs, P = self.camera_matrix)
                
       return dst       


    def cube_render(self, img = None):
        """DEPRECIATED
        Render a cube over an image
        
        DOESNT WORK AT THE MOMENT FOR SOME REASON! WONT SHOW IMAGE"""
        
        
        def draw(img, corners, imgpts):
            
            corner= tuple(corners[0].ravel())           
            
            img = cv2.line(img, corner, tuple(imgpts[0].ravel()), (255,0,0), 5)            
            img = cv2.line(img, corner, tuple(imgpts[1].ravel()), (0,255,0), 5)
            img = cv2.line(img, corner, tuple(imgpts[2].ravel()), (0,0,255), 5)
            
            return img
            
        def draw_cube(img, corners, imgpts):
            
            imgpts = np.int32(imgpts).reshape(-1,2)
            
            img = cv2.drawContours(img, [imgpts[:4]], -1, (0,255,0), -3)
            
            for i,j in zip(range(4), range(4,8)):
                img = cv2.line(img, tuple(imgpts[i]), tuple(imgpts[j]), (255), 3)
            
            img = cv2.drawContours(img, [imgpts[4:]], -1, (0,0,255), 3)
            
            return img

        
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001) 

        #Prepare object points, like (0,0,0), (1,0,0)... (8,5,0) 
        squares = (9,6)
        objp = np.zeros((np.prod(squares), 3), np.float32)
        objp[:,:2] = np.mgrid[0:squares[0], 0:squares[1]].T.reshape(-1,2)
        
        axis = np.float32([[3,0,0], [0,3,0], [0,0,-3]]).reshape(-1,3)
        
        axis = np.float32([[0,0,0], [0,3,0], [3,3,0], [3,0,0],
                           [0,0,-3], [0,3,-3], [3,3,-3], [3,0,-3]])
    
        if img == None:
            
            self.load_video()
            i = 0
            while True:
                print("Render Cube: Frame {}".format(i))
                i += 1
                ret, frame = self.cap.read()
                                
                if ret == False:
                    
                    break
                
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                ret2, corners = cv2.findChessboardCorners(gray, squares, None)   
               
                if ret2:
                    
                    corners2 = cv2.cornerSubPix(gray, corners, (11,11), (-1,-1), criteria)
                    
                    retval, rvecs, tvecs, inliers = cv2.solvePnPRansac(np.expand_dims(objp, axis = 1), corners2, self.mtx, self.dist)
                    
                    imgpts, jac = cv2.projectPoints(axis, rvecs, tvecs, self.mtx, self.dist)
                    
                    frame = draw_cube(frame, corners2, imgpts) #Renders cube
                
                
                cv2.imshow('show', frame) 
                cv2.waitKey(1)                
           
        
        self.cap.release()

        cv2.destroyAllWindows()
        
    def get_markers_blob(self):
        
        self.load_video()
        
        
        
        i = 0
        next_frame = True
        
#        cv2.namedWindow("TB")
#        cv2.createTrackbar("minThresh", "TB", 0,255, nothing)    
#        cv2.createTrackbar("maxThresh", "TB", 0,255, nothing)             
#        
#        cv2.createTrackbar("minArea", "TB", 0,255, nothing)         
#        cv2.createTrackbar("maxArea", "TB", 500,1500, nothing)         
#        cv2.createTrackbar("minCircularity", "TB", 8, 10, nothing)         
#        
#        cv2.createTrackbar("minConvex", "TB", 87,255, nothing) 
#        cv2.createTrackbar("minIntRatio", "TB", 5,255, nothing) 



        params = cv2.SimpleBlobDetector_Params()

        # Change thresholds
        params.minThreshold = 0
        params.maxThreshold = 255
        
        params.filterByColor = True
        params.blobColor = 255
        
        params.filterByArea = True
        params.minArea = 0
        params.maxArea = 1500
        
        params.filterByCircularity = True
        params.minCircularity = 0.1
        
        # Filter by Convexity
        params.filterByConvexity = True
        params.minConvexity = 0.1
            
        # Filter by Inertia
        params.filterByInertia = True
        params.minInertiaRatio = 0.01

        
        detector = cv2.SimpleBlobDetector_create(params)

        
        while True:
            
           print(i)  
           
           if next_frame:
               next_frame = False
               ret, frame = self.cap.read()
            
               if ret == False:
               
                   break 
           gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)  
           
#           cv2.imshow("gray", gray)
           
           
           keypoints = detector.detect(gray) 
           im_with_keypoints = cv2.drawKeypoints(gray, keypoints, np.array([]), (0,0,255), cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)

#           cv2.imshow("Raw", frame)    
           cv2.imshow("blobs", im_with_keypoints)
           key_press = cv2.waitKey(1) & 0xFF
           if  key_press == ord("n"):
               break
           next_frame= True
           i += 1
           if key_press == ord("p"):
               next_frame = True
               i += 1
        
    def get_markers(self):
        """Processs the video to get the IR markers
        Currently tracking a mobile phone light. May need to get a visible light filter to only allow IR light through"""        
        
        
        marker_file = "marker_data.csv"        
#        f = io.open(marker_file, 'w')           
        self.load_video()
        
        cv2.namedWindow("HSV TRACKBARS")
        cv2.createTrackbar("Hue low", "HSV TRACKBARS", 0,255, nothing)    
        cv2.createTrackbar("Hue high", "HSV TRACKBARS", 255, 255, nothing)  
        cv2.createTrackbar("Sat low", "HSV TRACKBARS", 0, 255, nothing)    
        cv2.createTrackbar("Sat high", "HSV TRACKBARS", 255, 255, nothing)  
        cv2.createTrackbar("Val low", "HSV TRACKBARS", 0, 255, nothing)    
        cv2.createTrackbar("Val high", "HSV TRACKBARS", 255, 255, nothing)        
        cv2.createTrackbar("Radius Low", "HSV TRACKBARS", 0, 50, nothing)  
        cv2.createTrackbar("Radius High", "HSV TRACKBARS", 50, 500, nothing)  
        
        i = 0
        next_frame = True
        
        while True:
            
           print(i)  
           
           if next_frame:
               next_frame = False
               ret, frame = self.cap.read()
            
               if ret == False:
               
                   break                   
               
           frame2 = frame.copy()    
           hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
           
           hue_low = cv2.getTrackbarPos("Hue low", "HSV TRACKBARS")
           hue_high = cv2.getTrackbarPos("Hue high", "HSV TRACKBARS")
           sat_low = cv2.getTrackbarPos("Sat low", "HSV TRACKBARS")
           sat_high = cv2.getTrackbarPos("Sat high", "HSV TRACKBARS")
           val_low = cv2.getTrackbarPos("Val low", "HSV TRACKBARS")
           val_high = cv2.getTrackbarPos("Val high", "HSV TRACKBARS")
           r_low = cv2.getTrackbarPos("Radius Low", "HSV TRACKBARS")
           r_high = cv2.getTrackbarPos("Radius High", "HSV TRACKBARS")
           
           lower_blue = np.array([hue_low, sat_low, val_low])
           upper_blue = np.array([hue_high, sat_high, val_high])
           
#           lower_blue = np.array([0,0,255])
#           upper_blue = np.array([255,255,255])
           
           mask = cv2.inRange(hsv, lower_blue, upper_blue)
           mask = cv2.erode(mask, None, iterations = 2)
           mask = cv2.dilate(mask, None, iterations = 2)          
           
           cnts = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]
           center = None
           
           if len(cnts) > 0:
               
               c = max(cnts, key = cv2.contourArea)
               ((x,y), radius) = cv2.minEnclosingCircle(c)
               M = cv2.moments(c)
               center = (int(M['m10'] / M['m00']), int(M['m01'] / M['m00']))
               
               if r_low < radius and radius < r_high:
                   
                   cv2.circle(frame2, (int(x), int(y)), int(radius), (0,0,255), 2 )
                   cv2.circle(frame2, (int(x), int(y)), 1, (255,0,255), 1 )
                   
                   cv2.circle(mask, (int(x), int(y)), int(radius), (0,0,255), 2 )
                   cv2.circle(mask, (int(x), int(y)), 1, (255,0,255), 1 )
                   
#                   f.write("{},{}\n".format(x,y))
                   
               else:
#                   f.write("{},{}\n".format(-9999, -9999))
                   pass
           
           cv2.imshow("Raw", frame2)
           cv2.imshow("Mask", mask)
           
           
           
           key_press = cv2.waitKey(1) & 0xFF
           if  key_press == ord("n"):
               break
           
           if key_press == ord("p"):
               next_frame = True
               i += 1
         
        f.close()   

    def ir_marker(self, img):
        """A function to get a single IR marker from and images. Returns the first marker it finds (So terrible if other IR light sources in)"""
                      
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        t_val = 100
        t, thresh = cv2.threshold(gray, t_val, 255, cv2.THRESH_BINARY)
       
        thresh = cv2.erode(thresh, None, iterations = 2)
        thresh = cv2.dilate(thresh, None, iterations = 2)       
       
        cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]
        center = None    

        if len(cnts) > 0:
            
           
            c = max(cnts, key = cv2.contourArea)
            ((x,y), radius) = cv2.minEnclosingCircle(c)
            M = cv2.moments(c)
            center = (int(M['m10'] / M['m00']), int(M['m01'] / M['m00']))
           
#                   if r_low < radius and radius < r_high:

            
            return (x,y), radius, center
        
        else:
            return None #Return NaN if no marker found
    
    
        
        
    def get_ir_markers(self, out_queue = None, plot = False):
        """Processs the video to get the IR markers
        
        Arguments:
            
            plot: Save plot images to the marker folder
        """
        
        if plot == True:
            
            plot_loc = self.kind
            print(self.kind)
        
        else:
            plot_loc = None        
            
        self.load_video()            
        
        all_markers = []
    
        i = 0
        
        last_markers, last_visible_markers = None, None
        while self.cap.isOpened():  
            
            ret, frame = self.cap.read()
            
            if not ret:
                
                self.cap.release()
                break
            
            ir = ir_marker.find_ir_markers(frame, n_markers = 3, it = i, tval = 150, last_markers = last_markers,
                                           last_visible_markers = last_visible_markers, plot_loc = plot_loc)
            last_markers = ir

            if not ir == None:
                last_visible_markers = ir 

            all_markers.append(ir) #Put results back into order
            
            i += 1            
        
        if out_queue != None:
            out_queue.put(all_markers)
        
        return all_markers
    
            
    def get_ir_markers_parallel(self, out_queue = None, max_jobs = 5, callback_function = None):                      
        """"Get IR markers from a video file. 
        out_queue is an optionally queue argument. If included the data will be put into the queue
        
        
        THERE IS A BUG HERE. THE WORKERS WILL NOT JOIN!!! 
        Seems to be working now OG- 23/03/17 DId i fix and forget to update text?
        """
            
        
        self.load_video() #Load the video
        
        #Create the Workers
        
#        max_jobs = 5 #Maximum number of items that can go in queue (may have to be small on RPi)    Now given as an argument
        jobs = multiprocessing.Queue(max_jobs)
        results = multiprocessing.Queue() #Queue to place the results into
      
        n_workers = multiprocessing.cpu_count()
    
        workers = []
        
        for i in range(n_workers):
            print("Starting Worker {}".format(i))
            tmp = multiprocessing.Process(target=ir_marker.get_ir_marker_process, args=(jobs,results,))
            tmp.start()
            workers.append(tmp)
        
            print("Worker started")
            
        
        
        print("There are {} workers".format(len(workers)))
        i = 0
        while self.cap.isOpened():  
                
            if not jobs.full():   
                ret, frame = self.cap.read()      
                
                if not ret:
                    self.cap.release()
                    break
                ID = i
                jobs.put([ID, frame]) #Put a job in the Queue (the frame is the job)
                if i%10 == 0:
                    if callback_function != None:
                        callback_function(i) #Call the progress update function
                    print("Get Markers Parallel: Job {} put in Queue".format(i))
                    
                i += 1
        
        print("Total jobs = {}".format(i))
        print("All jobs complete")
        N_jobs = i
        ##Tell all workers to Die
        for worker in workers:        
            print("KILLING MESSAGE")
            jobs.put("KILL")
                 
            
       
       #Get everything out the results queue into a list
        output = []
        N_jobs_returned = 0
        print("HERE")
        print(N_jobs)
        
        while (N_jobs_returned != N_jobs):
            
            dat = results.get()  
      
            output.append(dat)            
            N_jobs_returned += 1
#            print("RETURNED: {}, Total: {}".format(N_jobs_returned, N_jobs))
        
        print("KILL MY WORKERS")
           
        #Wait for workers to Die
        for worker in workers:               

            worker.join()
            
            print("Worker joined")
                
        self.v_loaded = False
                
        output.sort()

        if not np.alltrue(np.diff(np.array([i[0] for i in output])) == 1):
            raise Exception("ORDER PROBLEM")
           
        all_markers = [m[1] for m in output] #Get rid of marker ordering     
        

        #If a queue object exists put it into it. Useful if function is passed as a thread
        if out_queue != None:
            out_queue.put(all_markers)
                        
            
    
        return all_markers
    

      
class stereo_process:
    
    def __init__(self, cam_client, cam_serv, calibration_dir = None):
        """Pass two camera processing objects"""
        
        self.cam_serv = cam_serv
        self.cam_client = cam_client
        
        self.resolution = self.cam_client.resolution
        
        self.rectif = None #None if stereorectify has not been called
        
        if calibration_dir != None:

            calib_file = os.path.join(calibration_dir, 'stereo_camera_calib_params.pkl')

        else:
            
            calib_file = os.path.join(base_path, "calibration", 'stereo_camera_calib_params.pkl')        


        try:
            with open(calib_file, 'rb') as f:
                
                if sys.version_info[0] == 2:
                    self.stereo_calib_params = pickle.load(f) #Pickle is different in python 3 vs 2
          
                else:
                    self.stereo_calib_params = pickle.load(f, encoding = "Latin-1") #Load the calib parameters. [ret, mtx, dist, rvecs, tvecs]     
         
                self.retval, self.cameraMatrix1, self.distCoeffs1, self.cameraMatrix2, self.distCoeffs2, self.R, self.T, self.E, self.F, self.P1, self.P2 = self.stereo_calib_params
                print('Initialisation: Stereo Camera calibration parameters were found')
        except:            
            print("Initialisation: No stereo camera calibration parameters were found")
            
    def get_calibration_frames(self):
        """Allows us to choose images for calibrating the RPi Camera. The more the merrier (get lots of images from different angles"""
        
        resolution = (1280, 720) #Image resolution
        ##Check for previous files
        
        i = 0
        #Check for previous files
        master_dir = os.getcwd()
        
        if not os.path.exists(os.path.join(master_dir, 'calibration', 'stereo', 'client')):
            os.makedirs(os.path.join(master_dir, 'calibration', 'stereo', 'client'))
        
        if not os.path.exists(os.path.join(master_dir, 'calibration', 'stereo', 'server')):
            os.makedirs(os.path.join(master_dir, 'calibration', 'stereo', 'server'))
            
            
#        os.chdir(os.path.join(master_dir, "calibration", 'stereo')) #Go to the calibration images directory
        client_file_list = glob.glob(os.path.join(master_dir, "calibration", 'stereo', 'client', 'calib*'))
        server_file_list = glob.glob(os.path.join(master_dir, "calibration", 'stereo', 'server', 'calib*'))
        
        if (client_file_list != []) and (server_file_list != []):
            
            cont = input("Calibration images exist. Press 'c' to overwrite or 'a' to append. Any other key to cancel ")
            
            if cont.lower() == 'c':
                
                for f in client_file_list:
                    os.remove(f)
                
                for f in server_file_list:
                    os.remove(f)
                    
                     
            else:
                print("Escaping calibration")
                return 
        


        print("Camera Calibration: Loading Video")
        
        #Load both videos        
        self.cam_serv.load_video() #Make sure the calibration video is loaded      
        self.cam_client.load_video()           

        
        #Get first frame from both videos
        ret_serv, frame_serv = self.cam_serv.cap.read()
        ret_client, frame_client = self.cam_client.cap.read()
        
            

        cv2.namedWindow("Server", cv2.WINDOW_NORMAL)     
        cv2.namedWindow("Client", cv2.WINDOW_NORMAL)
#               cv2.resizeWindow("Raw", int(resolution[0]/2), int(resolution[1]/2)) 
        while True:
                                    
            
            if ret_serv == False or ret_client == False:
                print("Camera Calibration: No more Frames")
                self.cam_serv.cap.release()
                self.cam_client.cap.release()
                cv2.destroyAllWindows()
                
                self.cam_serv.v_loaded = False
                self.cam_client.v_loaded = False
                break
            
            cv2.imshow("Server", frame_serv)
            cv2.imshow("Client", frame_client)
            
            cv2.resizeWindow("Server", int(resolution[0]/2), int(resolution[1]/2)) 
            cv2.resizeWindow("Client", int(resolution[0]/2), int(resolution[1]/2)) 
            
            key_press = cv2.waitKey(1) & 0xFF
            
            if key_press == ord("n"):
                
                ret_serv, frame_serv = self.cam_serv.cap.read()
                ret_client, frame_client = self.cam_client.cap.read()
                
                continue
           
            elif key_press == ord("s"):         
                
                cv2.imwrite(os.path.join(os.getcwd(), 'calibration', 'stereo', 'server', 'calib_img_serv_{}.tiff'.format(i)), frame_serv)
                cv2.imwrite(os.path.join(os.getcwd(), 'calibration', 'stereo', 'client', 'calib_img_client_{}.tiff'.format(i)), frame_client)
                
#                np.save(os.path.join(os.getcwd(), 'calibration', 'calib_img_serv_{}'.format(i)), frame_serv)
#                np.save(os.path.join(os.getcwd(), 'calibration', 'calib_img_client_{}'.format(i)), frame_client)
                
                
                i += 1
                ret_serv, frame_serv = self.cam_serv.cap.read()
                ret_client, frame_client = self.cam_client.cap.read()#               
                continue
            
            elif key_press == ord("q"):
                self.cam_serv.cap.release()
                self.cam_client.cap.release()                
                cv2.destroyAllWindows()
                cv2.waitKey(1)
                self.cam_serv.v_loaded = False    
                self.cam_client.v_loaded = False
                break
        
    def stereo_calibrate(self):
        
        print("Running Stereo Calibration")
        master_dir = os.getcwd()
        
        os.chdir(os.path.join(master_dir, "calibration", 'stereo')) #Go to the calibration images
                
        client_dir = 'client'
        server_dir = 'server'

        img_names_client = glob.glob("{}/*tiff".format(client_dir))
        img_names_server = glob.glob("{}/*tiff".format(server_dir))
        
        if (len(img_names_client) == 0) and (len(img_names_server) == 0):
            
            img_names_client = glob.glob("{}/*jpeg".format(client_dir))
            img_names_server = glob.glob("{}/*jpeg".format(server_dir))
            
        img_names_client = natsort.humansorted(img_names_client)
        img_names_server = natsort.humansorted(img_names_server)
        
        
        square_size = float(37.5)

        pattern_size = (9, 6)
        pattern_points = np.zeros((np.prod(pattern_size), 3), np.float32)
        pattern_points[:, :2] = np.indices(pattern_size).T.reshape(-1, 2)
        pattern_points *= square_size
        
        
        self.obj_points = []
        self.img_points_client = []
        self.img_points_server = []
        h, w = 0, 0
        
        for fn in range(len(img_names_client)):
            print('processing %s... ' % img_names_client[fn], end='')
            print('processing %s... ' % img_names_server[fn], end='')
            
            img_client = cv2.imread(img_names_client[fn], 0)
            img_server = cv2.imread(img_names_server[fn], 0)
            
            if img_client is None:
                print("Failed to load", img_names_client[fn])
                continue
            
            if img_server is None:
                print("Failed to load", img_names_server[fn])
                continue
            
            h, w = img_client.shape[:2]
            
            found_client, corners_client = cv2.findChessboardCorners(img_client, pattern_size)
            found_server, corners_server = cv2.findChessboardCorners(img_server, pattern_size)
            
            if found_client and found_server:
                term = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_COUNT, 30, 0.1)                
                cv2.cornerSubPix(img_client, corners_client, (5, 5), (-1, -1), term)
                cv2.cornerSubPix(img_server, corners_server, (5, 5), (-1, -1), term)
                
            if not (found_client and found_server):
                print('chessboard not found in both images')
                continue  
           
            self.img_points_client.append(corners_client.reshape(-1,2))
            self.img_points_server.append(corners_server.reshape(-1,2))
            self.obj_points.append(pattern_points)
            
            print('ok')
    

     
        self.retval, self.cameraMatrix1, self.distCoeffs1, self.cameraMatrix2, self.distCoeffs2, self.R, self.T, self.E, self.F = cv2.stereoCalibrate(self.obj_points, self.img_points_client, self.img_points_server, 
                                                                                                     self.cam_client.camera_matrix, self.cam_client.dist_coefs,
                                                                                                     self.cam_serv.camera_matrix, self.cam_serv.dist_coefs, (w,h), flags = cv2.CALIB_FIX_INTRINSIC)
        
        self.P1 = np.dot(self.cameraMatrix1, np.hstack((np.identity(3),np.zeros((3,1)))))  #Projection Matrix for client cam
        self.P2 = np.dot(self.cameraMatrix2, np.hstack((self.R,self.T))) #Projection matrix for server cam
        print("\nRMS:", self.retval)     
        
        self.stereo_calib_params =  self.retval, self.cameraMatrix1, self.distCoeffs1, self.cameraMatrix2, self.distCoeffs2, self.R, self.T, self.E, self.F, self.P1, self.P2
        
        fname = os.path.join(os.path.dirname(os.getcwd()), 'stereo_camera_calib_params.pkl')
        
        with open(fname, 'wb') as f:
            pickle.dump(self.stereo_calib_params, f)    
        
        os.chdir(master_dir)
        
        print(self.R)
        print(self.T)
    
    def stereo_rectify(self):
        """
        DEPRECIATED
        This function only works when the image has resolution (1280, 720) """
        
#        self.T[0,0] = -100
        self.rectif = cv2.stereoRectify(self.cameraMatrix1, self.distCoeffs1, self.cameraMatrix2, self.distCoeffs2,
                                        (1280, 720), 
                                        self.R, self.T,
                                        flags = cv2.CALIB_ZERO_DISPARITY,
                                        alpha = 1, newImageSize=(0,0))
                                        
        self.R1, self.R2, self.P1, self.P2, self.Q, _o, _oo = self.rectif
        
        self.map1x, self.map1y = cv2.initUndistortRectifyMap(self.cameraMatrix1, self.distCoeffs1, self.R1, self.P1, (1280, 720), cv2.CV_32FC1)
        self.map2x, self.map2y = cv2.initUndistortRectifyMap(self.cameraMatrix2, self.distCoeffs2, self.R2, self.P2, (1280, 720), cv2.CV_32FC1)


        
    def triangulate(self, points1, points2):
        """NOT WORKING YET"""
        
        
        z = cv2.triangulatePoints(self.P1, self.P2, points1, points2)  
        
        z = (z / z[-1]).T
        z = z[:,:3]
        return z

    
    def test_triangulate(self, img1, img2):
        
        square_size = 24.5

        pattern_size = (9, 6)
        pattern_points = np.zeros((np.prod(pattern_size), 3), np.float32)
        pattern_points[:, :2] = np.indices(pattern_size).T.reshape(-1, 2)
        pattern_points *= square_size
        
        
        self.obj_points = []
        self.img_points_client = []
        self.img_points_server = []        
        h, w = 0, 0     

        
        img_client = img1
        img_server = img2  
        
        h, w = img_client.shape[:2]
        
        found_client, corners_client = cv2.findChessboardCorners(img_client, pattern_size)
        found_server, corners_server = cv2.findChessboardCorners(img_server, pattern_size)
        
        if found_client and found_server:
            term = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_COUNT, 30, 0.1)                
            cv2.cornerSubPix(img_client, corners_client, (5, 5), (-1, -1), term)
            cv2.cornerSubPix(img_server, corners_server, (5, 5), (-1, -1), term)
            
        if not (found_client and found_server):
            print('chessboard not found in both images')
            return None
              
        print('ok')
        return corners_client, corners_server     
        
    def triangulate_all_get_PL(self, client_markers, server_markers):
        """Get points from both videos and triangulate to 3d. Return path length measure.
        I should break this into smaller functions.
        This function is for code testing and will be very slow on the RPi. Use on desktop
        
        
        Update on 07/09/16
        Recoding to allow for multiple marker triangulation
        Points always have to be passed        
        """
        
        
        client_n_markers, server_n_markers = client_markers.shape[1], server_markers.shape[1]
        
        ##Make sure we have the correct number of markers in each camera
        assert client_n_markers == server_n_markers        
        
        #Force the markers to have the same number of frames by truncating the end of which ever is the longer marker array
        pos1_len = client_markers.shape[0]
        pos2_len = server_markers.shape[0]
        client_markers= client_markers[:min(pos1_len, pos2_len)]
        server_markers = server_markers[:min(pos1_len, pos2_len)]

                                        
        markers_3d_all = np.empty((client_markers.shape[0], client_markers.shape[1], 3)) #AN NxMx3 array of 3d marker positions
        
        ##Triangulate each marker point
        for mark in range(client_n_markers):
            
            pos1 = client_markers[:, mark]
            pos2 = server_markers[:, mark]
            
#            print(pos1.shape)
            pos1_undistort = self.cam_client.undistort_points(np.expand_dims(pos1, 0)).squeeze(axis = 0)
            pos2_undistort = self.cam_serv.undistort_points(np.expand_dims(pos2, 0)).squeeze(axis = 0)
            
            

            
                                            
            pos1_corrected, pos2_corrected = cv2.correctMatches(self.F, np.expand_dims(pos1_undistort, 0), np.expand_dims(pos2_undistort, 0)) 
            
            pos1_corrected, pos2_corrected = pos1_corrected.squeeze(), pos2_corrected.squeeze()
            
#            pos3d = self.triangulate(pos1_undistort.T, pos2_undistort.T)
            pos3d = self.triangulate(pos1_corrected.T, pos2_corrected.T)
            
            markers_3d_all[:,mark,:] = pos3d
        
        return markers_3d_all
        
    def kalman_smoother(self, markers_3d, init_cov = 1000, trans_cov = 0.5, obs_cov=3.0):
        """Filter the 3d marker points with a kalman smoother
        
        Must be an NxMX3 array where N is the number of data points and M is the number of markers. The last axis is the x,y,x position of the marker"""        
        
        n_markers = markers_3d.shape[1]
        
        filtered_markers = np.empty(markers_3d.shape)
        
        for mark in range(n_markers):
            
            
            pos3d = markers_3d[:,mark]
            kf = KalmanFilter(initial_state_mean=np.array([0, 0, 1000]), n_dim_obs=3)
        
            dt = 1/60
            transition_M = np.array([[1, 0, 0, dt, 0, 0],
                                     [0, 1, 0, 0, dt, 0],
                                     [0, 0, 1, 0, 0, dt],
                                     [0, 0, 0, 1, 0, 0],
                                     [0, 0, 0, 0, 1, 0],
                                     [0, 0, 0, 0, 0, 1]])
                      
            observation_M = np.array([[1,0,0,0,0,0], 
                                      [0,1,0,0,0,0], 
                                      [0,0,1,0,0,0]])
        
            measurements = np.ma.masked_invalid(pos3d)  
        
        
            initcovariance = init_cov * np.eye(6)
            transistionCov = trans_cov * np.eye(6)
            observationCov = obs_cov * np.eye(3)
                 
                            
            kf = KalmanFilter(transition_matrices = transition_M,  observation_matrices = observation_M, initial_state_covariance=initcovariance, transition_covariance=transistionCov,
                observation_covariance=observationCov)    

            (filtered_state_means, filtered_state_covariances) = kf.smooth(measurements)  
            
            filtered_markers[:,mark] = filtered_state_means[:,:3] #Don't return state covariance for a while
         
        return filtered_markers
    
    def kalman_smoother2(self, markers_3d, init_cov = 1000, trans_cov = 0.5, obs_cov=3.0):
        """Filter the 3d marker points with a kalman smoother.
        
        The same as kalman_smoother, but includes acceleration in the state space
        
        Must be an NxMX3 array where N is the number of data points and M is the number of markers. The last axis is the x,y,x position of the marker"""        
        
        n_markers = markers_3d.shape[1]
        
        filtered_markers = np.empty(markers_3d.shape)
        
        for mark in range(n_markers):
            
            
            pos3d = markers_3d[:,mark]
            kf = KalmanFilter(initial_state_mean=np.array([0, 0, 1000, 0, 0, 0, 0, 0, 0]), n_dim_obs=3)
        
            dt = 1/60
            transition_M = np.array([[1, 0, 0, dt, 0, 0, 0.5 * (dt**2), 0, 0],
                                     [0, 1, 0, 0, dt, 0, 0, 0.5 * (dt**2), 0],
                                     [0, 0, 1, 0, 0, dt, 0, 0, 0.5 * (dt**2)],
                                     [0, 0, 0, 1, 0, 0, dt, 0, 0],
                                     [0, 0, 0, 0, 1, 0, 0, dt, 0],
                                     [0, 0, 0, 0, 0, 1, 0, 0, dt],
                                     [0, 0, 0, 0, 0, 0, 1, 0, 0],
                                     [0, 0, 0, 0, 0, 0, 0, 1, 0],
                                     [0, 0, 0, 0, 0, 0, 0, 0, 1]])    

                      
            observation_M = np.array([[1,0,0,0,0,0,0,0,0], 
                                      [0,1,0,0,0,0,0,0,0], 
                                      [0,0,1,0,0,0,0,0,0]])
        
            measurements = np.ma.masked_invalid(pos3d)  
        
        
            initcovariance = init_cov * np.eye(9)
            transistionCov = trans_cov * np.eye(9)
            observationCov = obs_cov * np.eye(3)
                 
                            
            kf = KalmanFilter(transition_matrices = transition_M,  observation_matrices = observation_M, initial_state_covariance=initcovariance, transition_covariance=transistionCov,
                observation_covariance=observationCov)    

            (filtered_state_means, filtered_state_covariances) = kf.smooth(measurements)  
            
            filtered_markers[:,mark] = filtered_state_means[:,:3] #Don't return state covariance for a while
         
        return filtered_markers
        
    def zero_order_butterworth(self, markers_3d, order = 10, fs = 60, cutoff = 8):
        """Zero order butterworth filter"""
        
        n_markers = markers_3d.shape[1]
        
        filtered_markers = np.empty(markers_3d.shape)
        
        for mark in range(n_markers):       
        
            filtered_markers[:,mark, 0] = butter_lowpass_filter(markers_3d[:, mark, 0], cutoff, fs, order)
            filtered_markers[:,mark, 1] = butter_lowpass_filter(markers_3d[:, mark, 1], cutoff, fs, order)
            filtered_markers[:,mark, 2] = butter_lowpass_filter(markers_3d[:, mark, 2], cutoff, fs, order)
        
        return filtered_markers

    
    
def butter_lowpass(cutoff, fs, order=5):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    return b, a

def butter_lowpass_filter(data, cutoff, fs, order=5):
    b, a = butter_lowpass(cutoff, fs, order=order)
    y = filtfilt(b, a, data)
    return y
                
class myThread(threading.Thread):
    """A simple thread class. Pass an ID and name for the thread. Pass a function and any arguments to execute in thread"""
    def __init__(self, threadID, name, func, *args, **kwargs):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.func = func
        self.args = args
        self.kwargs = kwargs
        
    def run(self):
        
        self.func(*self.args, **self.kwargs)
        
      
def check_timestamp_error():
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
        
        raise IOError("The time stamps are not in sync")
    
    return 


def cam_server():
    """Run a standard server program"""
    
    myCam = posturalCam() #Create a camera class
    myCam.TCP_server_start()


def cam_client(t):
    """Run a standard client program"""
    
    myCam = posturalCam()    
    myCam.TCP_client_start()
    
    
#    myCam.videoPreview()
#    myCam.TCP_client_request_videoPreview()
    
#    while True:
#        f1 = myCam.TCP_client_poll_videoPreview()
#        f2 = myCam.poll_videoPreview()
#        
#        if(f1 != None) and (f2 != None):
#            print("F1: {}, F2: {}".format(f1.shape, f2.shape))
    
    myCam.TCP_client_start_UDP(t, 'testIR.h264') #Starts the video recording
    myCam.TCP_client_request_timestamps()
    check_timestamp_error()
    myCam.TCP_client_request_video()   
    myCam.TCP_client_close()
#    
#    
#    self.backend_camera.TCP_client_start_UDP(t, 'testIR.h264') #Starts the video recording       
#        self.backend_camera.TCP_client_request_timestamps() #Request time stamps
#        self.check_timestamp_error() #Check if there are any problems with the time stamps   
#    
#    
#    proc = posturalProc(v_fname = 'testIR.h264', kind = 'client')
#    proc.check_v_framerate(f_name = 'time_stamps.csv')
#    proc2 = posturalProc(v_fname = 'testIR_server.h264', kind = 'server')  
#    proc2.check_v_framerate(f_name = 'timestamps_server.csv')

#    stereo = stereo_process(proc, proc2)
    
#    PL, points2 = stereo.triangulate_all_get_PL(points[0], points[1])
    
    

#    pdb.set_trace()
    #Ana


def cam_get_x_vids(x):
    """x is the number of videos to get
    
    DEPRECIATED"""
    
    fnames = ['test_video_{}.h264'.format(i) for i in range(x)]
    
    myCam = posturalCam()    
    
    
    for f in fnames:
        myCam.TCP_client_start()
        myCam.TCP_client_start_UDP(15, f) 
        myCam.TCP_client_request_video()      
        myCam.TCP_client_close()
    
def main(t):
    
   # Check who we are
    global networked
    networked = True #If True will run networked protocol. First checks IP address. If Server run server program. If client run client program
     
    
#    pdb.set_trace()
    if networked:
        ip_addr = subprocess.check_output(['hostname', '-I']).decode().strip(" \n") #Get IP address
        
        if ip_addr == '192.168.0.2':
            mode = 'client'     
#            print("I am a {}".format(mode))       
           
            cam_client(t)
#            cam_get_x_vids(1) #Start the client camera 
            
            
        elif ip_addr == '192.168.0.3':
            mode = 'server'
            print("I am a {}".format(mode))
            cam_server()
   
    

def check_synchrony():
    """Test the synchrony between the two RPi's. 
    Take two videos of a timer (a fast clock) and name them 'test_video_0.h264' and 'test_video_server_0.h264'
    This function will play the frames back frame by frame so you can assess the camera synchrony"""
    
    
    
    fnames = ['test_video_{}.h264'.format(i) for i in range(1)]
    
    for video_fname in fnames:
        split_name = video_fname.split('.')
        video_server_fname = '{}_server.{}'.format(split_name[0], split_name[1])
       
        server_cam = posturalProc(0, v_fname = video_server_fname)
        client_cam = posturalProc(0, v_fname = video_fname)
        
        server_cam.load_video()
        client_cam.load_video()
        
        ret1, sf = server_cam.cap.read()
        ret2, cf = client_cam.cap.read()
        
        while True:
            
            if ret1 and ret2:
                cv2.imshow('serverCam', np.fliplr(sf))
                cv2.imshow('clientCam', np.fliplr(cf))
            
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('n'):
                ret1, sf = server_cam.cap.read()
                ret2, cf = client_cam.cap.read()
            if key == ord('q'):
                cv2.destroyAllWindows()
                break
  


def test_stereo_calibration():
    """Test the calibration of the stereo cameras.
    Requires two videos names as in the function. 
    This will grab images of a chessboard and reconstruct it in 3D space. Then check the distance between points and plot a histogram"""
    
    proc = posturalProc(v_fname = 'calib_vid_0.h264', kind = 'client')
    proc2 = posturalProc(v_fname = 'calib_vid_0_server.h264', kind = 'server')    
    

    stereo = stereo_process(proc, proc2)

    img1 = cv2.imread('calibration\\stereo\\client\\calib_img_client_12.tiff',0) #the zero argument makes grayscale (wont work otherwise)
    img2 = cv2.imread('calibration\\stereo\\server\\calib_img_serv_12.tiff',0)
    
    img_p1, img_p2 = stereo.test_triangulate(img1, img2)  
    
    
    img_p1 = proc.undistort_points(img_p1) #Remove extra dimension    
    img_p2 = proc.undistort_points(img_p2) #Remove extra dimension
    plt.figure()
    plt.imshow(img1, cmap = 'gray')
    
    img_p1_o, img_p2_o = cv2.correctMatches(stereo.F, img_p1.transpose(1,0,2), img_p2.transpose(1,0,2)) #Must be in format 1XNX2
#    print(img_p1.transpose(1,0,2).shape)
    img_p1, img_p2 = img_p1.squeeze(), img_p2.squeeze()
    img_p1_o, img_p2_o = img_p1_o.squeeze(), img_p2_o.squeeze()
    plt.figure()
    plt.scatter(img_p1[:,0], img_p1[:,1], color = 'b', s = 100)
    plt.scatter(img_p2[:,0], img_p2[:,1], color = 'r', s = 100)
    plt.scatter(img_p1[:,0], img_p1[:,1], color = 'g')
    plt.scatter(img_p2[:,0], img_p2[:,1], color = 'y')
    
    P1 = np.dot(stereo.cameraMatrix1, np.hstack((np.identity(3),np.zeros((3,1))))) 
    P2 = np.dot(stereo.cameraMatrix2, np.hstack((stereo.R,stereo.T)))
    
    
  
    z = cv2.triangulatePoints(P1, P2, img_p1_o.T, img_p2_o.T)  
    z = (z / z[-1]).T
    z = z[:,:3]
    

    
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.scatter(z[:,0], z[:,1], z[:,2])
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Z")
    plt.show()
    
    
    p_diff = np.sqrt(np.square(np.diff(z, axis = 0)).sum(1))        
    p_diff = np.append(p_diff, -999)
    
    
    plt.figure()
    sns.distplot(p_diff.reshape((6,9))[:,:-1].flatten())
    
#proc.get_calibration_frames()
#proc.camera_calibration()
#proc.play_video()
#proc.get_markers()
#proc.check_camera_calibration()
    
def calibration_protocol():
    """A function to calibrate all the cameras"""
    
    proc = posturalProc(v_fname = 'testIR.h264', kind = 'client')
    proc2 = posturalProc(v_fname = 'testIR_server.h264', kind = 'server')    
    
#    proc.get_calibration_frames()
#    proc2.get_calibration_frames()
    
#    proc.camera_calibration()    
#    proc2.camera_calibration()
    
    stereo = stereo_process(proc, proc2)
    stereo.get_calibration_frames() #You will need to then place the calibration images into the correct folders (Set this up to do automatically)
    stereo.stereo_calibrate()
#    print(stereo.R)
#    print(stereo.T)
    
    
def marker_tracking3d_test():
    
    proc = posturalProc(v_fname = 'testIR.h264', kind = 'client')
    proc2 = posturalProc(v_fname = 'testIR_server.h264', kind = 'client')
    
#    proc2.play_video()

    proc_all_markers = ir_marker.markers2numpy(proc.get_ir_markers())
    proc2_all_markers = ir_marker.markers2numpy(proc2.get_ir_markers())
    
    stereo =  stereo_process(proc, proc2)
        
    markers3d = stereo.triangulate_all_get_PL(proc_all_markers, proc2_all_markers) #Get the marker positions in 3d space   
    
    distance_between_leds = np.sqrt(np.sum(np.square(np.diff(markers3d, axis = 1)), axis = 2)).squeeze()
    
    distance_between_leds_nan = distance_between_leds[np.isfinite(distance_between_leds)]
    
    plt.plot(distance_between_leds_nan)
#    sns.distplot(distance_between_leds_nan)
def vector_magnitude(v):
    """Calculate the magnitude of a vector"""
    
    #Check that v is a vector
    if v.ndim != 1:
        raise TypeError("Input is not a vector")
    return np.sqrt(np.sum(np.square(v)))  
    
if __name__ == '__main__':

    cam_server() #Run a server cam
