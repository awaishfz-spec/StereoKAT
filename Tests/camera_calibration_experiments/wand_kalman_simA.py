# -*- coding: utf-8 -*-
"""
Created on Thu Sep  8 16:27:02 2016

@author: ps09og
"""
from __future__ import division, print_function
import numpy as np
import matplotlib.pylab as plt
from mpl_toolkits.mplot3d import Axes3D


def create_wand(length = 100):    
    
    wand = np.empty((3,3))
    
    wand[1] = [0,0,0]
    wand[0] = [wand[1,0] - length/2, 0, 0]
    wand[2] = [wand[1,0] + length/2, 0, 0]
    
    
    return wand
    
def translation(p, x, y, z):
    
    T = np.array([x, y, z])
    
    return p + T
    
        
wand = create_wand() 

fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')
ax.scatter(wand[:,0], wand[:,1], wand[:,2], s = 50, depthshade = False)
ax.plot(wand[:,0], wand[:,1], wand[:,2], color = 'k')
ax.view_init(elev=94., azim=-90)
ax.set_xlabel("X")
ax.set_ylabel("Y")
ax.set_zlabel("Z")
ax.set_xlim([-20, 500])
ax.set_ylim([-20, 500])
ax.set_zlim([-20, 500])
plt.gca().invert_yaxis()
plt.gca().invert_zaxis()
plt.title("Standard Wand")


###Position of wand center
p_x = np.sin(np.linspace(0,50,1000)*0.5) * 100
p_y = np.sin(np.linspace(0,50,1000)) * 50
p_z = np.sin(np.linspace(0,50,1000)*0.5) * 500

dt = 1 /60
dt2 = dt

def time_stamp(dt, length = 1000):
    
    ts = np.empty(length)

    for i in range(length-1):
        ts[i+1] = ts[i] + dt
    
    return ts

ts = time_stamp(dt)


pos3d = np.vstack((p_x, p_y, p_z)).T

vel3d = np.diff(pos3d, axis = 0) / dt
acc3d = np.diff(vel3d, axis = 0) / dt

pos3d = pos3d  + np.random.normal(0, 10, size = pos3d.shape)

fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')
ax.scatter(pos3d[:,0], pos3d[:,1], pos3d[:,2], s = 50, depthshade = False)
ax.view_init(elev=94., azim=-90)
ax.set_xlabel("X")
ax.set_ylabel("Y")
ax.set_zlabel("Z")
ax.set_xlim([-20, 500])
ax.set_ylim([-20, 500])
ax.set_zlim([-20, 500])
plt.gca().invert_yaxis()
plt.gca().invert_zaxis()
plt.title("Standard Wand")


plt.close()

#A = np.array(   [[1, 0, 0, dt, 0, 0, 0.5 * dt**2, 0, 0],
#                [0, 1, 0, 0, dt, 0, 0, 0.5 * dt**2, 0],
#                [0, 0, 0, 0, 0, dt, 0, 0, 0.5 * dt**2],
#                [0, 0, 0, 1, 0, 0, dt, 0, 0],
#                [0, 0, 0, 0, 1, 0, 0, dt, 0],
#                [0, 0, 0, 0, 0, 1, 0, 0, dt],
#                [0, 0, 0, 0, 0, 0, 1, 0, 0],
#                [0, 0, 0, 0, 0, 0, 0, 1, 0],
#                [0, 0, 0, 0, 0, 0, 0, 0, 1] ])
                
A = np.array([[1, dt, 0.5 * (dt**2)],
              [0, 1,            dt],
              [0, 0,            1]])
                
import pystan

code = """

data{

    int N; //Number of data points
    int K; //Number of dimensions of data

    real Y[N]; //Data
    matrix[K*3,K*3] A;

}

parameters{

    real<lower = 0> Sigma;   
    real<lower = 0> Sig;
    vector[K*3] X[N];
}

transformed parameters{ 
    
  
}


model{

    X[1] ~ normal(500, 2000);
    
    for (i in 2:N){
        X[i] ~ normal(A * X[i-1], Sig); 
    }
    
    Sigma ~ cauchy(0,10);
    Y ~ normal(X[1:N, 1], Sigma);
    //Y[1:N, 2] ~ normal(X[1:N, 2], Sigma);
    //Y[1:N, 3] ~ normal(X[1:N, 3], Sigma);

}

"""


sm = pystan.StanModel(model_code=code)

stan_data = {'Y': pos3d[:,0], 'N': pos3d.shape[0], 'K': 1, 'A': A}

fit = sm.sampling(data = stan_data, chains = 1, iter = 500, refresh = 1)
#op = sm.optimizing(data = stan_data)


with open('print_fit.txt', 'w') as f: #Save fit print output to file
    print(fit, file=f)
    
la = fit.extract()

plt.plot(pos3d[:,0], 'or')
plt.plot(la['X'].mean(0)[:,0], 'b-')
