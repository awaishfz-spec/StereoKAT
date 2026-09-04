# -*- coding: utf-8 -*-
"""

"""

import os
import numpy as np
import pickle
import glob
import matplotlib.pylab as plt

#with open(os.path.join(os.getcwd(), "calibration", calib_fname), 'rb') as f:
#                if sys.version_info[0] == 2:
#                    self.calib_params = pickle.load(f) #Pickle is different in python 3 vs 2
#                else:
#                    self.calib_params = pickle.load(f, encoding = "Latin-1") #Load the calib parameters. [ret, mtx, dist, rvecs, tvecs]     
#                self.rms, self.camera_matrix, self.dist_coefs, self.rvecs, self.tvecs = self.calib_params

calib_files = glob.glob("*.pkl")

rms_all = []
camera_matrix_all = []
dist_coefs_all = []

for cal in calib_files:
    
    with open(cal, 'rb') as f:
        calib_params = pickle.load(f)
    rms, camera_matrix, dist_coefs, rvecs, tvecs = calib_params
    
    rms_all.append(rms)
    camera_matrix_all.append(camera_matrix)
    dist_coefs_all.append(dist_coefs)
    

rms_all = np.array(rms_all)
camera_matrix_all = np.array(camera_matrix_all)
dist_coefs_all = np.array(dist_coefs_all)


calib_params = rms_all.mean(0), np.average(camera_matrix_all, axis = 0, weights = 1/rms_all), np.average(dist_coefs_all, axis = 0, weights = 1/rms_all), rvecs, tvecs

with open('client_camera_calib_params.pkl', 'wb') as f:
    pickle.dump(calib_params, f)