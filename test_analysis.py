# -*- coding: utf-8 -*-
"""
"""

import posturalCam_master_NETWORK as backend
import ir_marker
import numpy as np
import matplotlib.pylab as plt

import time

if __name__ == '__main__':
    
    fname = 'M:\\Adult_PSAT\\recorded_data\\AAtkinson\\Record_0\\videos\\'
    
    t0 = time.time()
    proc = backend.posturalProc(v_fname = fname + 'testIR_server.h264', kind = 'client')
    
    markers = ir_marker.markers2numpy(proc.get_ir_markers(plot = True))
    
    t1 = time.time()
        
    print("That took {} seconds".format(t1 -t0))
    
    print(markers[60:80,0,:])
    