# -*- coding: utf-8 -*-
"""
Camera calibration procedure for the postural camera system

"""

import posturalCam_master_NETWORK as backend


def calibrate_client():
    """Calibrate the left camera"""
    proc = backend.posturalProc(v_fname = 'testIR.h264', kind = 'client')
    proc.get_calibration_frames()
    proc.camera_calibration()
    
def calibrate_client_preview():
    """Calibrate the left camera"""
    proc = backend.posturalProc(kind = 'client_preview')

    proc.camera_calibration()
    
def calibrate_server():
    """Calibrate the right camera"""
    proc = backend.posturalProc(v_fname = 'testIR_server.h264', kind = 'server')
    proc.get_calibration_frames()
    proc.camera_calibration()

def calibrate_server_preview():
    """Calibrate the left camera"""
    proc = backend.posturalProc(kind = 'server_preview')

    proc.camera_calibration()

def stereo_calibrate():
    """Calibrate the stereo cameras extrinic parameters"""
    proc = backend.posturalProc(v_fname = 'testIR.h264', kind = 'client')
    proc2 = backend.posturalProc(v_fname = 'testIR_server.h264', kind = 'server')    
    stereo = backend.stereo_process(proc, proc2)
    
    stereo.get_calibration_frames() #You will need to then place the calibration images into the correct folders (Set this up to do automatically)
    stereo.stereo_calibrate()    

def calibrate_stereo_preview():
    
    proc = backend.posturalProc(v_fname = 'testIR.h264', kind = 'client_preview')
    proc2 = backend.posturalProc(v_fname = 'testIR_server.h264', kind = 'server_preview')    
    stereo = backend.stereo_process(proc, proc2)
    
    stereo.get_calibration_frames() #You will need to then place the calibration images into the correct folders (Set this up to do automatically)
#    stereo.stereo_calibrate()    
    
    return stereo

if __name__ == '__main__':
    
    """Comment out the functions you dont want to call by placing a # before them.
    Any problems contact Oscar Giles o.t.giles@leeds.ac.uk"""
    
#    calibrate_client() #Calibrate intrinsics of camera 1
#    calibrate_client_preview() #Calibrate intrinsics of camera 1 (Preview mode)
    
    calibrate_server() #Calibrate intrinsics of camera 2
#    s = calibrate_stereo_preview()
#    stereo_calibrate() #Calibrate stereo rig (camera extrinsics)
    
    