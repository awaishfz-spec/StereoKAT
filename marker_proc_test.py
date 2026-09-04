# -*- coding: utf-8 -*-
"""

"""

import posturalCam_master_NETWORK as backend
import ir_marker
import numpy as np
import matplotlib.pylab as plt
import multiprocessing

if __name__ == '__main__':
    fname = 'F:\\ogtestPSAT\\recorded_data\\tt2\\Record_0\\videos\\'
    
    proc = backend.posturalProc(v_fname = fname + 'testIR.h264', kind = 'client')
    proc2 = backend.posturalProc(v_fname = fname + 'testIR_server.h264', kind = 'server')
    
    procb = backend.posturalProc(v_fname = fname + 'testIR.h264', kind = 'client')
    proc2b = backend.posturalProc(v_fname = fname + 'testIR_server.h264', kind = 'server')   
       
    client_markers = proc.get_ir_markers()
    server_markers = proc2.get_ir_markers()
    
    
    
    
    client_markers2 = procb.get_ir_markers_parallel(max_jobs = 20)
    server_markers2 = proc2b.get_ir_markers_parallel(max_jobs = 20)


    client_all_markers = backend.ir_marker.markers2numpy(client_markers)
    server_all_markers = backend.ir_marker.markers2numpy(server_markers[:client_all_markers.shape[0]])
                                                        
    client_all_markers2 = backend.ir_marker.markers2numpy(client_markers2)
    server_all_markers2 = backend.ir_marker.markers2numpy(server_markers2[:client_all_markers2.shape[0]])
    
    client_all_markers = np.nan_to_num(client_all_markers)
    server_all_markers = np.nan_to_num(server_all_markers)
    client_all_markers2 = np.nan_to_num(client_all_markers2)
    server_all_markers2 = np.nan_to_num(server_all_markers2)
 
    assert(np.all(client_all_markers==client_all_markers2))
    assert(np.all(server_all_markers==server_all_markers2))