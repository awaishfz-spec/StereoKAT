# -*- coding: utf-8 -*-
"""

"""

import posturalCam_master_NETWORK as backend
import ir_marker
import numpy as np
import matplotlib.pylab as plt

fname = 'G:\\Adult_PSAT\\recorded_data\\ExpOne\\EBerry\\Record_1\\videos\\'

proc = backend.posturalProc(v_fname = fname + 'testIR.h264', kind = 'client')
proc2 = backend.posturalProc(v_fname = fname + 'testIR_server.h264', kind = 'server')

stereo =  backend.stereo_process(proc, proc2)

proc_all_markers = backend.ir_marker.markers2numpy(proc.get_ir_markers(plot = False))
proc2_all_markers = backend.ir_marker.markers2numpy(proc2.get_ir_markers(plot = False))[:proc_all_markers.shape[0]]

markers3d = stereo.triangulate_all_get_PL(proc_all_markers, proc2_all_markers) #Get the marker positions in 3d space   

marker_mid_3d = np.sum(markers3d, axis = 1)/2.0


markers3d_filt = stereo.kalman_smoother(markers3d, init_cov = 1000, trans_cov = 0.4, obs_cov = 6.0)
 
markers3d_filt[np.isnan(markers3d)] = np.NaN #Make values where no data was recorded NaN
marker_mid_3d_filt = np.sum(markers3d_filt, axis = 1)/2.0

#plt.plot(marker_mid_3d[:,0])
dist_nofilt = np.sqrt(np.sum(np.square(np.diff(marker_mid_3d, axis = 0)), axis = 1))
dist = np.sqrt(np.sum(np.square(np.diff(marker_mid_3d_filt, axis = 0)), axis = 1))


#dist[dist < 0.15] = 0.0
#plt.plot(dist)
#plt.plot(dist_nofilt)

fig, ax = plt.subplots(4,1, sharex = True, figsize = (10, 8))
ax[0].plot(marker_mid_3d[:,0])
ax[0].plot(marker_mid_3d_filt[:,0])
ax[1].plot(marker_mid_3d[:,1])
ax[1].plot(marker_mid_3d_filt[:,1])
ax[2].plot(marker_mid_3d[:,2])
ax[2].plot(marker_mid_3d_filt[:,2])
#ax[3].plot(dist_nofilt)
ax[3].plot(dist)

ax[0].set_ylabel("x pos")
ax[1].set_ylabel("y pos")
ax[2].set_ylabel("z pos")
ax[3].set_ylabel("d (mm)")

ax[-1].set_xlabel("Frame")
#    distance_between_leds = np.sqrt(np.sum(np.square(np.diff(markers3d, axis = 1)), axis = 2)).squeeze()
#    distance_between_leds_filt = np.sqrt(np.sum(np.square(np.diff(markers3d_filt, axis = 1)), axis = 2)).squeeze()