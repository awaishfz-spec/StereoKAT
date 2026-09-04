# -*- coding: utf-8 -*-
"""

"""

import posturalCam_master_NETWORK as backend
import ir_marker
import numpy as np
import matplotlib.pylab as plt
from scipy.signal import butter, filtfilt, freqz
import os

def butter_lowpass(cutoff, fs, order=5):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    return b, a

def butter_lowpass_filter(data, cutoff, fs, order=5):
    b, a = butter_lowpass(cutoff, fs, order=order)
    y = filtfilt(b, a, data)
    return y






fname = 'F:\\ogtestPSAT\\recorded_data\\p01\\Record_0\\'
#calibration_dir = 'F:\\ogtestPSAT\\recorded_data\\p01\\Record_0\\calibration\\'
#
#proc = backend.posturalProc(v_fname = fname + 'testIR.h264', calibration_dir = calibration_dir, kind = 'client')
#proc2 = backend.posturalProc(v_fname = fname + 'testIR_server.h264', calibration_dir = calibration_dir, kind = 'server')
#
#stereo =  backend.stereo_process(proc, proc2, calibration_dir)
#
#proc_all_markers = backend.ir_marker.markers2numpy(proc.get_ir_markers(plot = False))
#proc2_all_markers = backend.ir_marker.markers2numpy(proc2.get_ir_markers(plot = False))[:proc_all_markers.shape[0]]
#
#markers3d = stereo.triangulate_all_get_PL(proc_all_markers, proc2_all_markers) #Get the marker positions in 3d space   
#marker_mid_3d = np.sum(markers3d, axis = 1)/2.0
#
#
#
#
#
#markers3d_filt = stereo.kalman_smoother(markers3d, init_cov = 1000, trans_cov = 0.4, obs_cov = 6.0)
#
#
#
#
#
# 
#markers3d_filt[np.isnan(markers3d)] = np.NaN #Make values where no data was recorded NaN
#marker_mid_3d_filt = np.sum(markers3d_filt, axis = 1)/2.0
#
##plt.plot(marker_mid_3d[:,0])
#dist_nofilt = np.sqrt(np.sum(np.square(np.diff(marker_mid_3d, axis = 0)), axis = 1))
#dist = np.sqrt(np.sum(np.square(np.diff(marker_mid_3d_filt, axis = 0)), axis = 1))


#dist[dist < 0.15] = 0.0
#plt.plot(dist)
#plt.plot(dist_nofilt)

marker_mid_3d = np.loadtxt(os.path.join(fname, 'mid3D_unfiltered.csv'), skiprows = 1, delimiter = ',')
marker_mid_3d_filt = np.loadtxt(os.path.join(fname, 'mid3D_filtered.csv'), skiprows = 1, delimiter = ',')


fig, ax = plt.subplots(4,1, sharex = True, figsize = (10, 8))
ax[0].plot(marker_mid_3d[:,0])
ax[0].plot(marker_mid_3d_filt[:,0])
ax[1].plot(marker_mid_3d[:,1])
ax[1].plot(marker_mid_3d_filt[:,1])
ax[2].plot(marker_mid_3d[:,2])
ax[2].plot(marker_mid_3d_filt[:,2])
#ax[3].plot(dist_nofilt)

ax[0].set_ylabel("x pos")
ax[1].set_ylabel("y pos")
ax[2].set_ylabel("z pos")
ax[3].set_ylabel("d (mm)")

ax[-1].set_xlabel("Frame")



###########Butter filter

# Filter requirements.
order = 10
fs = 60.0       # sample rate, Hz
cutoff = 8  # desired cutoff frequency of the filter, Hz

# Get the filter coefficients so we can check its frequency response.
b, a = butter_lowpass(cutoff, fs, order)

# Plot the frequency response.
w, h = freqz(b, a, worN=8000)
plt.subplot(4, 1, 1)
plt.plot(0.5*fs*w/np.pi, np.abs(h), 'b')
plt.plot(cutoff, 0.5*np.sqrt(2), 'ko')
plt.axvline(cutoff, color='k')
plt.xlim(0, 0.5*fs)
plt.title("Lowpass Filter Frequency Response")
plt.xlabel('Frequency [Hz]')
plt.grid()


# Filter the data, and plot both the original and filtered signals.
y1 = butter_lowpass_filter(marker_mid_3d[:,0], cutoff, fs, order)
y2 = butter_lowpass_filter(marker_mid_3d[:,1], cutoff, fs, order)
y3 = butter_lowpass_filter(marker_mid_3d[:,2], cutoff, fs, order)

plt.subplot(4, 1, 2)
plt.plot(marker_mid_3d[:,0], 'b-', label='data')
plt.plot(y1, 'g-', linewidth=2, label='filtered data')
plt.xlabel('Time [sec]')
plt.grid()
plt.legend()

plt.subplot(4, 1, 3)
plt.plot(marker_mid_3d[:,1], 'b-', label='data')
plt.plot(y2, 'g-', linewidth=2, label='filtered data')
plt.xlabel('Time [sec]')
plt.grid()
plt.legend()

plt.subplot(4, 1, 4)
plt.plot(marker_mid_3d[:,2], 'b-', label='data')
plt.plot(y3, 'g-', linewidth=2, label='filtered data')
plt.xlabel('Time [sec]')
plt.grid()
plt.legend()

plt.subplots_adjust(hspace=0.35)



plt.show()
#    distance_between_leds = np.sqrt(np.sum(np.square(np.diff(markers3d, axis = 1)), axis = 2)).squeeze()
#    distance_between_leds_filt = np.sqrt(np.sum(np.square(np.diff(markers3d_filt, axis = 1)), axis = 2)).squeeze()