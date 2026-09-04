# -*- coding: utf-8 -*-
"""



This script can be used to save images from the camera preview in order to do the calibration for the camera preview triangulation
"""

from posturalCam_master_NETWORK import *
import cv2


def get_preview_calibration(kind = "client"):
    """
    Save images to for the camera calibration for the camera preview    
    Choose the kind of calibration from 'Client', 'Server' or 'Stereo'
    """
    
    #Start feed from Server camera
    backend_camera = posturalCam() 
    backend_camera.TCP_client_start()
    backend_camera.TCP_client_request_videoPreview()
    
    
    #Start feed from client camera
    previewVid = NN_PiVideoClient(sensor_mode = 6, framerate = 30, resolution = (1280, 720), resize = (640, 368))
    previewVid.start()
    
    
    #Start showing Frames
    i = 0 #Number of frame being saved
    while True:
    
        client_frame = previewVid.read()
        server_frame = backend_camera.TCP_client_poll_videoPreview()
        
        
        if (client_frame != None) and (server_frame != None):
            client_frame = client_frame[:,:,::-1]
            server_frame = server_frame[:,:,::-1]
            cv2.imshow("Client", client_frame)
            cv2.imshow("Server", server_frame)
            
            key_press = cv2.waitKey(1) & 0xFF
            
                    
            if key_press == ord("q"):
                break
        
            elif key_press == ord("s"):      
                print("Save Image")
                if kind == 'client':
                    cv2.imwrite(os.path.join(os.getcwd(), 'calibration', 'client_preview', 'calib_img_{}.jpeg'.format(i)), client_frame)
                elif kind == 'server':
                    cv2.imwrite(os.path.join(os.getcwd(), 'calibration', 'server_preview', 'calib_img_{}.jpeg'.format(i)), server_frame)
                
                elif kind == 'stereo':
                    cv2.imwrite(os.path.join(os.getcwd(), 'calibration', 'stereo_preview', 'client', 'calib_img_client_{}.tiff'.format(i)), client_frame)
                    cv2.imwrite(os.path.join(os.getcwd(), 'calibration', 'stereo_preview', 'server', 'calib_img_serv_{}.tiff'.format(i)), server_frame)
                
                i += 1
               
                continue
         
    #Close down the preview
    previewVid.stop()
    backend_camera.TCP_client_stop_videoPreview()
    
    #Close down the connection to the server
    backend_camera.TCP_client_close()
    
if __name__ == '__main__':
    
    get_preview_calibration(kind = 'stereo')