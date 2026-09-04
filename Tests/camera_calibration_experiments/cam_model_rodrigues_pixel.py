# -*- coding: utf-8 -*-
"""
Created on Wed Jul 27 12:46:42 2016

@author: Oscar Giles

Camera model used for camera calibration. Aim is to make a Bayesian calibration model and to learn about the model

"""

from __future__ import print_function, division
import numpy as np
import itertools
import pdb
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import seaborn as sns
#import cv2
import pickle
#import stanplotting as sp

def create_chessboard(squares = (6,9), square_size = 24.5):    
    
    objp = np.zeros((np.prod(squares), 3), np.float32)
    
    p = itertools.product(np.arange(0,square_size*squares[0],square_size), np.arange(0,square_size*squares[1],square_size))
    objp[:,:2] = np.array([i for i in p])[:,::-1]
    
    
    
    return objp

def rotation(p, x, y, z):
    """Rotate point p by angle x, y, z"""
    
    Rx = np.array([[1, 0, 0],
                   [0, np.cos(x), -np.sin(x)],
                    [0, np.sin(x), np.cos(x)]])
                    
    Ry = np.array([[np.cos(y), 0, np.sin(y)],
                   [0, 1 , 0],
                    [-np.sin(y), 0 , np.cos(y)]])       
                    
    Rz = np.array([[np.cos(z), -np.sin(z), 0],
                   [np.sin(z), np.cos(z) , 0],
                    [0, 0, 1]])
                    
    
                    
    R = np.dot(Rx, np.dot(Ry, Rz))
   
    return np.dot(R, p), R

def translation(p, x, y, z):
    
    T = np.array([x, y, z])
    
    return p + T
    
def get_RT_matrix(rotation, translation):
    """Return homogenous RT matrix where the 3rd collumn has been dropped"""
    Rx = np.array([[1, 0, 0],
                   [0, np.cos(rotation[0]), -np.sin(rotation[0])],
                    [0, np.sin(rotation[0]), np.cos(rotation[0])]])
                    
    Ry = np.array([[np.cos(rotation[1]), 0, np.sin(rotation[1])],
                   [0, 1 , 0],
                    [-np.sin(rotation[1]), 0 , np.cos(rotation[1])]])       
                    
    Rz = np.array([[np.cos(rotation[2]), -np.sin(rotation[2]), 0],
                   [np.sin(rotation[2]), np.cos(rotation[2]) , 0],
                    [0, 0, 1]])            
                        
    R = np.dot(Rx, np.dot(Ry, Rz))
    
    
    T = np.array(translation)
    
    RT = np.hstack((R, np.expand_dims(T, 1))) #Append T to last collumn of R
        
    
    return RT[:,[0,1,3]]

def get_camera_matrix(fx, fy, cx, cy, s):
    """Return a camera Matrix A
    input:
    fx: focal length x
    fy: focal length y
    cx: offset x
    cy: offset y
    s: skew parameter
    """
    
    return np.array([[fx, s, cx],
                     [0, fy, cy],
                     [0, 0, 1 ]])

def get_homography_matrix(M, RT):
    """Given the camera matrix M and the RT matrix (R1, R2, T) return the homography matrix H"""
    
    return np.dot(M, RT)
    
def mm_to_pixel(p_mm, k_x, k_y, resolution):
    
    c = np.array([k_x, k_y, 1])
    
    
    return p_mm * c + np.array([resolution[0]/ 2, resolution[1]/2, 0])
    
def rodrig(v, k):
    """Rotate vector v around vector k by a magnitude equal to the lenght of k"""
    
    theta = np.sqrt(np.dot(k,k))
    
    return v * np.cos(theta) + np.cross(k, v) * np.sin(theta) + k * np.dot(k,v) * (1-np.cos(theta))    

def cross(a,b):
    
    return np.array([a[1]*b[2] - a[2]*b[1], a[2]*b[0] - a[0]*b[2], a[0]*b[1] - a[1]*b[0]])
    
plot_example = True


##Camera parameters
fx, fy = 10, 3.5 #Camera focal length
cx, cy = 0.0, 0.0 #Offsets of the camera center 
resolution = (1280, 720) #Camera resolution
width, height = 5.0, 5.0 #sensor dimensions 
s = 0 #Skew parameter
sigma = 1.0
kx, ky = resolution[0]/ width, resolution[1] / height #Scalling factor to convert screen coordinates in mm to pixels

fx_p, fy_p = fx * kx, fy * ky
cx_p, cy_p = cx * kx , cy * ky 


#Create a chess board    
chessboard = create_chessboard()    
chessboardH = chessboard.copy()
chessboardH[:,-1] = 1

if plot_example:
    plt.scatter(chessboard[:,0], chessboard[:,1]) #Plot the chessboard
    plt.gca().invert_yaxis()

if plot_example:
    #Plot the chessboard in 3D
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.scatter(chessboard[:,0], chessboard[:,1], chessboard[:,2], depthshade = True)
    ax.view_init(elev=94., azim=-90)
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Z")
    ax.set_xlim([-20, 500])
    ax.set_ylim([-20, 500])
    ax.set_zlim([-20, 500])
    plt.gca().invert_yaxis()
    plt.gca().invert_zaxis()
    plt.title("Standard Chessboard")
    
    #PLOT CHESSBOARD CENTER
    ax.scatter(width/2, height/2, 0, color = 'r', s = 50)
    #plt.show()
    


M = get_camera_matrix(fx_p, fy_p, cx_p, cy_p, s) #Camera Intrinsic matrix in pixels   

#Image rotations and translations
#rot_trans =  [[(-np.pi/5, np.pi/4, 0), (200, 80, 400)],
#              [(np.pi/6, np.pi/8, 0.0), (50, 20, 300)],
#              [(-np.pi/3, -np.pi/4, 0.0), (60, 10, 355)],
#              [(np.pi/2.5, -np.pi/8, np.pi/3.5), (55, 20, 600)],
#              [(-np.pi/3.2, np.pi/6.7, 0.0), (45, 22, 400)],
#              [(np.pi/3.8, -np.pi/4.2, 0.0), (87, 46, 357)],
#              [(-np.pi/4, np.pi/8, 0.0), (465, 46, 438)],]
#rot_trans =  [[(-np.pi/5, np.pi/4, 0), (200, 80, 400)],
#              [(np.pi/6, np.pi/8, 0.0), (50, 20, 300)],]
#              [(-np.pi/3, -np.pi/4, 0.0), (60, 10, 355)]]
              
#              [(np.pi/2.5, -np.pi/8, np.pi/3.5), (55, 20, 600)],
#              [(-np.pi/3.2, np.pi/6.7, 0.0), (45, 22, 400)],
#              [(np.pi/3.8, -np.pi/4.2, 0.0), (87, 46, 357)],
#              [(-np.pi/4, np.pi/8, 0.0), (465, 46, 438)],]
       
rod = np.array([[-0.6, 0.24, .3],
                [0.3, 0.5, .2],
                [-0.8, -.9, .8],
                [0.74, .84, 1.]
                ]) #Rotations       
                
trans = np.array([[-24.5 * 8 / 2.0, -24.5 * 5 / 2.0, 250],
                  [10, -50, 350],
                  [20, 30, 500],
                  [-30, -65, 250],
                  ]) #Translations. First one is dead center
              
all_imagepointspx = [] #Empty array to put all images points in



#Get all the images
for rt in range(len(rod)):
    
   
    chessboard_new = np.empty(chessboard.shape, dtype = np.float32)
    imgpoints_new = np.empty(chessboard.shape, dtype = np.float32)
    imgpointspx_new = np.empty(chessboard.shape, dtype = np.float32) 

    #RT = get_RT_matrix(rt[0], rt[1])    
    #H = get_homography_matrix(M, RT)

    for c in range(len(chessboard)):   
        
        chessboard_new[c] = rodrig(chessboard[c], rod[rt]) + trans[rt]  #Chessboards position in space
        imgpoints_new[c] = np.dot(M, chessboard_new[c])   #Chessboard mapped to image
        imgpoints_new[c] = imgpoints_new[c] / imgpoints_new[c][-1] + np.array([resolution[0]/ 2, resolution[1]/2, 0]) #Divide through by Z to make w = 1 and add some noise
        imgpointspx_new[c] = imgpoints_new[c] + np.append(np.random.normal(0, sigma, size = 2), 0) 
    
    all_imagepointspx.append(imgpointspx_new)        
    
    if plot_example:
          
        fig = plt.figure()
        ax2 = fig.add_subplot(111, projection='3d')
        ax2.scatter(chessboard_new[:,0], chessboard_new[:,1], chessboard_new[:,2], depthshade = True)
        ax2.text(chessboard_new[0,0],chessboard_new[0,1], chessboard_new[0,2],  '0', size=20, zorder=1,  
                color='k') 
        ax2.text(chessboard_new[-1,0],chessboard_new[-1,1], chessboard_new[-1,2],  '-1', size=20, zorder=1,  
                color='k') 
                
        ax2.view_init(elev=94., azim=-90)
        ax2.set_xlabel("X")
        ax2.set_ylabel("Y")
        ax2.set_zlabel("Z")
        ax2.set_xlim([-20, 500])
        ax2.set_ylim([-20, 500])
        ax2.set_zlim([-20, 500])
        plt.gca().invert_yaxis()
        plt.gca().invert_zaxis()
        ax2.scatter(width/2, height/2, 0, color = 'r', s = 50) ##CENTER OF CAMERA
        plt.title("RT chessboard")
#        #Plot the chessboards projection onto the camera
        
        fig2 = plt.figure()        
        plt.scatter(imgpointspx_new[:,0], imgpointspx_new[:,1])
#        plt.axvline(width/2)
#        plt.axhline(height/2)
        plt.xlim([0, resolution[0]])
        plt.ylim([0, resolution[1]])
        plt.axvline(resolution[0]/2, color = 'k')
        plt.axhline(resolution[1]/2, color = 'k')
        plt.gca().invert_yaxis()
        plt.title("Camera Projection")
        
plt.close('all')       
###############################
################################
######Bayesian Analysis#########

import pystan

#sm = pickle.load(open('bayesianCam_mult_rodrig_pixel_stan.pkl', 'rb'))
sm = pystan.StanModel(file='bayesianCam_mult_rodrig_pixel_trans.stan') #Compile Stan Model
with open('bayesianCam_mult_rodrig_pixel_stan.pkl', 'wb') as f: #Save Stan model to file
    pickle.dump(sm, f)

all_imagepointspx = np.array(all_imagepointspx)

img_points = np.load("img_points.npy")
obj_points = np.load("obj_points.npy")

obj_points = obj_points[0]
#stan_images = all_imagepointspx[:,:,:2].flatten()
stan_images = img_points.squeeze().flatten()
stan_data = dict(images = stan_images, 
                 P = len(img_points), 
                 K = 54, 
                 chessboard = obj_points, 
                 resolution = resolution)

def init_pars():
    
    _sigma = 1 + np.random.lognormal(0, 5)
    _fx_p = fx_p + np.random.normal(0, 100)
    _fy_p = fy_p + np.random.normal(0, 100)
    _cx = resolution[0]/2
    _cy = resolution[1]/2
    _r1 = rod[:,0] + np.random.normal(0, 0.5, size = (rod.shape[0]))
    _r2 = rod[:,1] + np.random.normal(0, 0.5, size = (rod.shape[0]))
    _r3 = rod[:,2] + np.random.lognormal(0, 0.5, size = (rod.shape[0]))
    
    return {'sigma': _sigma,  'fx': _fx_p, 'fy': _fy_p , 'cx': _cx,  'cy': _cy, 'r1': _r1, 'r2': _r2, 'r3': _r3 }
    
#init = [{'sigma': 1,  'fx': fx_p, 'fy': fy_p , 'cx': resolution[0]/2,  'cy': resolution[1]/2, 'r1': rod[:,0], 'r2': rod[:,1], 'r3': rod[:,2],
#         't1': trans[:,0], 't2': trans[:,1], 't3': trans[:,2] }]

#def raw_scale(x, mean, sd):
#    
#    return (x-mean) / sd
#    
#init2 = [{'sigma_unif': 1,  'fx_raw': raw_scale(fx_p, 600, 300), 'fy_raw': raw_scale(fy_p, 800, 300), 'cx_raw': raw_scale(resolution[0]/2, 360, 50),  'cy_raw': raw_scale(resolution[0]/2, 640, 50), 
#         'r1_raw': raw_scale(rod[:,0], 0, 0.5), 'r2_raw': raw_scale(rod[:,1], 0 ,0.5), 'r3_raw': raw_scale(rod[:,2], 0, 1), 't1_raw': raw_scale(trans[:,0], 0, 50), 
#         't2_raw': raw_scale(trans[:,1], 0, 50), 't3_raw': raw_scale(trans[:,2], 0, 300) }]
#


fit = sm.sampling(data=stan_data, iter = 50, chains=4, 
                      refresh = 1, init = 'random', init_r = 0.5,
                      control = {'adapt_delta': 0.99, 'max_treedepth': 20}) #Fit model  
                      
#fit = sm.sampling(data=stan_data, iter = 1, raw_scale(resolution[0]/2, 360, 50)
#                      algorithm = 'Fixed_param') #Fit model  

print(fit)

sampler_params = fit.get_sampler_params(inc_warmup=False) 
n_divergent = reduce(lambda x, y: x + y['divergent__'].tolist(), sampler_params, []) 

if 1 in n_divergent: 
    print("N divergent = {}".format(sum(n_divergent)))      
    with open("error logging.csv", 'a') as f:
        f.write("N divergent = {}\n".format(sum(n_divergent)))      
    
else:
    print("N divergent = {}".format(0))                                

la = fit.extract(permuted = True)

with open('print_fit.txt', 'w') as f: #Save fit print output to file
            print(fit, file=f)
            
plt.figure()
plt.plot(la['fx'])


plt.figure()
sns.distplot(la['fx'])
plt.title("fx: {}".format(fx_p))

plt.figure()
sns.distplot(la['fy'])
plt.title("fy: {}".format(fy_p))

plt.figure()
sns.distplot(la['cx'])
plt.title("cx: {}".format(cx_p +resolution[0]/2))

plt.figure()
sns.distplot(la['cy'])
plt.title("cy: {}".format(cy_p+resolution[1]/2))

plt.figure()
sns.distplot(la['sigma'])
plt.title("sigma: {}".format(sigma))

#plt.figure()
#sp.errorplot(rod[:,0], la['r1'])
#
#plt.figure()
#sp.errorplot(rod[:,1], la['r2'])
#
#plt.figure()
#sp.errorplot(rod[:,2], la['r3'])
##
#plt.figure()
#sns.distplot(la['r3'][:,0])
#plt.title("r3: {}".format(rot_trans[0][0][2]))
