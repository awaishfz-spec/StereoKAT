# -*- coding: utf-8 -*-
"""

"""

import os
import numpy as np
import pickle
import glob
import pdb

#with open(os.path.join(os.getcwd(), "calibration", calib_fname), 'rb') as f:
#                if sys.version_info[0] == 2:
#                    self.calib_params = pickle.load(f) #Pickle is different in python 3 vs 2
#                else:
#                    self.calib_params = pickle.load(f, encoding = "Latin-1") #Load the calib parameters. [ret, mtx, dist, rvecs, tvecs]     
#                self.rms, self.camera_matrix, self.dist_coefs, self.rvecs, self.tvecs = self.calib_params

calib_files = glob.glob("*.pkl")

ret_all = []
R_all = []
T_all = []
E_all = []
F_all = []
P1_all = []
P2_all = []


for cal in calib_files:
    print(cal)
    with open(cal, 'rb') as f:
        calib_params = pickle.load(f)
        
    retval, cameraMatrix1, distCoeffs1, cameraMatrix2, distCoeffs2, R, T, E, F, P1, P2 = calib_params

    print(R)
    
    ret_all.append(retval)
    R_all.append(R)
    T_all.append(T)
    E_all.append(E)
    F_all.append(F)
    P1_all.append(P1)
    P2_all.append(P2)
    
ret_all = np.array(ret_all)
R_all = np.array(R_all)
T_all = np.array(T_all)
E_all = np.array(E_all)
F_all = np.array(F_all)
P1_all = np.array(P1_all)
P2_all = np.array(P2_all)



calib_params = retval, cameraMatrix1, distCoeffs1, cameraMatrix2, distCoeffs2, R_all.mean(0), T_all.mean(0), E_all.mean(0), F_all.mean(0), P1_all.mean(0), P2_all.mean(0)


with open('stereo_camera_calib_params.pkl', 'wb') as f:
    pickle.dump(calib_params, f)