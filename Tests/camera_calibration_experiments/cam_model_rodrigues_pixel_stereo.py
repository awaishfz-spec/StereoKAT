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




class camera:
    """A camera simulation"""
    def __init__(self, fx, fy, cx, cy, width, height, resolution, s, sigma = 0.5, T = None, R = None):
        
        self.fx = fx
        self.fy = fy
        self.cx = cx
        self.cy = cy
        self.width, self.height = width, height
        self.resolution = resolution
        self.s = s        
        self.sigma = sigma # How noisy is the camera (doesnt effect any methods or do anything)
        
        self.kx = resolution[0] / width
        self.ky = resolution[1] / height
        
        self.fx_p = fx * self.kx
        self.fy_p = fy * self.ky
        
        self.cx_p = cx * self.kx + resolution[0]/2
        self.cy_p = cy * self.ky + resolution[1]/2
        
        self.trans_cam = False
        
        if T == None:
            self.T = np.array([0,0,0])
        else:
            self.T = T
            self.trans_cam = True
            
        if R == None:
            self.R = np.array([0,0,0])
        else:
            self.R = R
        
        self.M = get_camera_matrix(self.fx_p, self.fy_p, self.cx_p, self.cy_p, self.s)
        
    def position_object(self, obj, rod, tran):
        """Place object in space by rotating with rodrigues vector rod and translate with tran"""        
        object_new = np.empty(chessboard.shape, dtype = np.float32)
        for c in range(len(obj)):              
            
            object_new[c] = rodrig(rodrig(obj[c], rod) + tran, -self.R) - self.T  #Chessboards position in space
            
        return object_new

    def project_object(self, obj):
        """Project an object onto the camera sensor and return it in pixel coordinates"""
        projected_new = np.empty(chessboard.shape, dtype = np.float32)
        
        for c in range(len(obj)):              
            projected_img = np.dot(self.M, obj[c])
            projected_new[c] = projected_img / projected_img[-1]
        
        return projected_new
       
    def plot_standard_object(self, obj):
        """Plot the object at the world space origin"""
        
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        ax.scatter(obj[:,0], obj[:,1], obj[:,2], depthshade = True)
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
        ax.scatter(self.width/2, self.height/2, 0, color = 'r', s = 50)
        
    def plot_object(self, obj):
        """Plot an object in space"""
        
        fig = plt.figure()
        ax2 = fig.add_subplot(111, projection='3d')
        ax2.scatter(obj[:,0], obj[:,1], obj[:,2], depthshade = True)
        ax2.text(obj[0,0],obj[0,1], obj[0,2],  '0', size=20, zorder=1,  
                color='k') 
        ax2.text(obj[-1,0],obj[-1,1], obj[-1,2],  '-1', size=20, zorder=1,  
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
        ax2.scatter(self.width/2, self.height/2, 0, color = 'r', s = 50) ##CENTER OF CAMERA
        plt.title("RT chessboard")
        
        return ax2 #Return this so we can plot to it later
        
    def plot_projection(self, proj):
        """Plot a projected image"""
        
        fig2 = plt.figure()        
        plt.scatter(proj[:,0], proj[:,1])

        plt.xlim([0, self.resolution[0]])
        plt.ylim([0, self.resolution[1]])
        plt.axvline(self.resolution[0]/2, color = 'k')
        plt.axhline(self.resolution[1]/2, color = 'k')
        plt.gca().invert_yaxis()
        
        if self.trans_cam:
            plt.title("Camera Projection Trans")
        else:
            plt.title("Camera Projection Stand")
    
#Create a chess board    
chessboard = create_chessboard() 


##Create the left camera        
cl = camera(fx=3.5, fy=3.5, cx=0, cy=0, width=5.0, height=5.0, resolution=(1280,720), s=0)      

##Create the right camera
cr = camera(fx=3.5, fy=3.5, cx=0, cy=0, width=5.0, height=5.0, resolution=(1280,720), s=0, 
            T = np.array([100,0,10]), R = np.array([0, -np.pi/10, 0]))  

rod = np.array([[0,0,0], [0,0,.5]]) #Rotations       
                
trans = np.array([[-24.5 * 8 / 2.0, -24.5 * 5 / 2.0, 350], [50, 50, 1000]]) #Translations. First one is dead center
           
           
           
all_imagepointspx_1 = [] #Empty array to put all images points in
all_imagepointspx_2 = []

for rt in range(len(rod)):
    
    object_pos = cl.position_object(chessboard, rod[rt], trans[rt]) 
    object_pos2 = cr.position_object(chessboard, rod[rt], trans[rt]) 
    
    
    cl.plot_object(object_pos)

    projection = cl.project_object(object_pos)
    projection2 = cr.project_object(object_pos2)
    
    ##Add noise
    
    projection[:,:2] = projection[:,:2] + np.random.normal(0, cl.sigma, projection[:,:2].shape)
    projection2[:,:2] = projection2[:,:2] + np.random.normal(0, cr.sigma, projection2[:,:2].shape)
    
    #Quantize 

    projection = projection.round()
    projection2 = projection2.round()    
    
    all_imagepointspx_1.append(projection)
    all_imagepointspx_2.append(projection2)
    
    cl.plot_projection(projection)
    cr.plot_projection(projection2)

        
      
###############################
################################
######Bayesian Analysis#########

import pystan


##sm = pickle.load(open('bayesianCam_mult_rodrig_pixel_stan.pkl', 'rb'))
#sm = pystan.StanModel(file='bayesianCam_mult_rodrig_pixel_trans.stan') #Compile Stan Model
#with open('bayesianCam_mult_rodrig_pixel_stan.pkl', 'wb') as f: #Save Stan model to file
#    pickle.dump(sm, f)
#
#all_imagepointspx = np.array(all_imagepointspx)

#img_points = np.load("img_points.npy")
#obj_points = np.load("obj_points.npy")

#obj_points = obj_points[0]
##stan_images = all_imagepointspx[:,:,:2].flatten()
#stan_images = img_points.squeeze().flatten()
#stan_data = dict(images = stan_images, 
#                 P = len(img_points), 
#                 K = 54, 
#                 chessboard = obj_points, 
#                 resolution = resolution)
#
#def init_pars():
#    
#    _sigma = 1 + np.random.lognormal(0, 5)
#    _fx_p = fx_p + np.random.normal(0, 100)
#    _fy_p = fy_p + np.random.normal(0, 100)
#    _cx = resolution[0]/2
#    _cy = resolution[1]/2
#    _r1 = rod[:,0] + np.random.normal(0, 0.5, size = (rod.shape[0]))
#    _r2 = rod[:,1] + np.random.normal(0, 0.5, size = (rod.shape[0]))
#    _r3 = rod[:,2] + np.random.lognormal(0, 0.5, size = (rod.shape[0]))
#    
#    return {'sigma': _sigma,  'fx': _fx_p, 'fy': _fy_p , 'cx': _cx,  'cy': _cy, 'r1': _r1, 'r2': _r2, 'r3': _r3 }
#    
##init = [{'sigma': 1,  'fx': fx_p, 'fy': fy_p , 'cx': resolution[0]/2,  'cy': resolution[1]/2, 'r1': rod[:,0], 'r2': rod[:,1], 'r3': rod[:,2],
##         't1': trans[:,0], 't2': trans[:,1], 't3': trans[:,2] }]
#
##def raw_scale(x, mean, sd):
##    
##    return (x-mean) / sd
##    
##init2 = [{'sigma_unif': 1,  'fx_raw': raw_scale(fx_p, 600, 300), 'fy_raw': raw_scale(fy_p, 800, 300), 'cx_raw': raw_scale(resolution[0]/2, 360, 50),  'cy_raw': raw_scale(resolution[0]/2, 640, 50), 
##         'r1_raw': raw_scale(rod[:,0], 0, 0.5), 'r2_raw': raw_scale(rod[:,1], 0 ,0.5), 'r3_raw': raw_scale(rod[:,2], 0, 1), 't1_raw': raw_scale(trans[:,0], 0, 50), 
##         't2_raw': raw_scale(trans[:,1], 0, 50), 't3_raw': raw_scale(trans[:,2], 0, 300) }]
##
#
#
#fit = sm.sampling(data=stan_data, iter = 8000, chains=4, 
#                      refresh = 1, init = 'random', init_r = 0.75,
#                      control = {'adapt_delta': 0.9, 'max_treedepth': 20}) #Fit model  
#                      
##fit = sm.sampling(data=stan_data, iter = 1, raw_scale(resolution[0]/2, 360, 50)
##                      algorithm = 'Fixed_param') #Fit model  
#
#print(fit)
#
#sampler_params = fit.get_sampler_params(inc_warmup=False) 
#n_divergent = reduce(lambda x, y: x + y['divergent__'].tolist(), sampler_params, []) 
#
#if 1 in n_divergent: 
#    print("N divergent = {}".format(sum(n_divergent)))      
#    with open("error logging.csv", 'a') as f:
#        f.write("N divergent = {}\n".format(sum(n_divergent)))      
#    
#else:
#    print("N divergent = {}".format(0))                                
#
#la = fit.extract(permuted = True)
#
#plt.figure()
#plt.plot(la['fx'])
#
#
#plt.figure()
#sns.distplot(la['fx'])
#plt.title("fx: {}".format(fx_p))
#
#plt.figure()
#sns.distplot(la['fy'])
#plt.title("fy: {}".format(fy_p))
#
#plt.figure()
#sns.distplot(la['cx'])
#plt.title("cx: {}".format(cx_p +resolution[0]/2))
#
#plt.figure()
#sns.distplot(la['cy'])
#plt.title("cy: {}".format(cy_p+resolution[1]/2))
#
#plt.figure()
#sns.distplot(la['sigma'])
#plt.title("sigma: {}".format(sigma))
#
##plt.figure()
##sp.errorplot(rod[:,0], la['r1'])
##
##plt.figure()
##sp.errorplot(rod[:,1], la['r2'])
##
##plt.figure()
##sp.errorplot(rod[:,2], la['r3'])
###
##plt.figure()
##sns.distplot(la['r3'][:,0])
##plt.title("r3: {}".format(rot_trans[0][0][2]))
