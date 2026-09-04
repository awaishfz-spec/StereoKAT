# -*- coding: utf-8 -*-
"""

"""

import cv2
import matplotlib.pylab
import numpy as np
import multiprocessing
import matplotlib.pylab as plt
import pdb, os

def get_ir_marker_process(jobs, results):
    """multiprocessing function"""        
         
        
    while True:            
      
        in_job = jobs.get() #Get the job ID and the job
   
 
        if isinstance(in_job, str):
            
            if in_job == "KILL":     
                
                break                   
                            
        
        else:         
            ID, j = in_job[0], in_job[1]
       
            ir = find_ir_markers(j, n_markers = 2, it = ID, tval = 150)
            
                      
            out = [ID, ir] #Place in results queue with the ID

       
            
        results.put(out)
    
    return
    



def find_ir_markers(frame, n_markers = 2, it = 0, tval = 150, last_markers = None, plot_loc = None):
    """A wrapper for the find_ir_markers function. Filter markers by area and adaptively call find_ir_markers
    
    Optionally pass the position of the markers in the last frame to narrow the search area"""
    
    if plot_loc == None:
        
        plot = False #Save results 
    
    else:
        plot = True
        
        dirs = [".\\markers\\found\\client\\", ".\\markers\\found\\server\\", ".\\markers\\not_found\\client\\", ".\\markers\\not_found\\server\\"]
        
        for d in dirs:
            if not os.path.exists(d):
                os.makedirs(d)
  
    ax = None
    if plot:
        f, ax = plt.subplots(1,1)
        ax.imshow(frame[:,:,::-1])
        plt.suptitle("Frame: {}".format(it))
        
  
    tval = 125   #Lower threshold for thresholding brightness
    
    if last_markers == None:
        #Initial guess        
        ir = find_ir_markers_nofilt(frame, it = it, tval = tval, gamma = None, plot_ax = None)   
    
    else:
        
        old_marker_pos = np.array([i['pos'] for i in last_markers])
     
        padding = 25 #give 20px padding
        
        
        x_min, x_max = np.min(old_marker_pos[:,0]), np.max(old_marker_pos[:,0])
        y_min, y_max = np.min(old_marker_pos[:,1]), np.max(old_marker_pos[:,1])
        
        x_min_floor, x_max_floor = int(np.max([0, x_min - padding])), int(np.min([frame.shape[1], x_max + padding]))
        y_min_floor, y_max_floor = int(np.max([0, y_min - padding])), int(np.min([frame.shape[0], y_max + padding]))
        
  
        if (y_min_floor == y_max_floor) or (x_min_floor == x_max_floor):
            
            ir = None
        
        else:
            #Now reduce the frame size
            frame_new = np.copy(frame)     
            frame_new = frame_new[ y_min_floor:y_max_floor, x_min_floor: x_max_floor]     
          

            
            ir = find_ir_markers_nofilt(frame_new, it = it, tval = tval, gamma = None, plot_ax = None) 
        
        #If no markers found run it again with the whole image
        if ir == None:      
           
            ir = find_ir_markers_nofilt(frame, it = it, tval = tval, gamma = None, plot_ax = None)   
        
        else:
            
            for marker in ir:
                
                marker['pos'] = (marker['pos'][0] + x_min_floor, marker['pos'][1] + y_min_floor)
#                marker['center'] = (int(marker['pos'][0] + x_min_floor), int(marker['pos'][1] + x_max_floor))
                
                
    #####IF NO MARKER FOUND DO SOMETHING HERE
    if ir == None:
        if plot:
            plt.savefig(".\\markers\\not_found\\{}\\frame_{}.png".format(plot_loc, it)) 
        return None
    
    
    ##IF MARKERS FOUND BUT ONE IS SUPER LARGE THIS PROBABLY MEANS THERE IS GLARE
    
    max_area = 40 #Maximum area of marker acceptable
    min_area = 7 #Minimum area of marker acceptable
    
    if ir != None:

        rads_max = [mark['radius'] <= max_area for mark in ir] #Check radius of all markers is less than or equal area max
        rads_min = [min_area <= mark['radius'] for mark in ir] #Check radius of all markers is greater than or equal marker min
        
        
        #If marker area is too big it likely indicates either glare or external IR sources 
        if False in rads_max: #
            print("Marker glare. Trying again")
           
            ####LETS TRY TO RUN IT AGAIN WITH A HIGH GAMMA CORRECTION
            ir = find_ir_markers_nofilt(frame, it = it, tval = tval, gamma = 5, plot_ax = None) #Try IR with a very high threshold
            
            if ir == None:
                if plot:
                    plt.savefig(".\\markers\\not_found\\{}\\frame_{}.png".format(plot_loc, it)) 
                return None
                
            
                
            rads_max = [mark['radius'] <= max_area for mark in ir] #Check radius of all markers is less than or equal area max
            rads_min = [min_area <= mark['radius'] for mark in ir] #Check radius of all markers is greater than or equal marker min
    
        
#    if (it == 357):
#        f, ax = plt.subplots(1,1)
#        ax.imshow(frame[:,:,::-1])
#        plt.suptitle("Frame: {}".format(it))    
#        for mark in ir:
#            
#            circle1 = plt.Circle(mark['pos'], mark['radius'] , color='b', fill = False, linewidth = 2)
#            ax.add_artist(circle1)  
#        plt.show()        
#        pdb.set_trace()
    ##Now filter the markers        
                   
    if ir != None:
        len_ir = len(ir)
        if len_ir > 0:
            mask = rads_max            
            ir = np.extract(mask, ir) #Remove markers that are too large               
            
            compactness_error = np.array([np.abs(mark['compactness'] - 1) for mark in ir])
            
#            print([i['radius'] for i in ir])
            #IF there are more than n_markers only get the largest radius markers 
            if len(ir) > n_markers:
                ir = ir[compactness_error < 1] #Remove non circular objects
                
                ir = sorted(ir, key = lambda x: x['radius'], reverse = True) #Order by IR radius size                  
                ir = ir[:n_markers] #Try to get the number of markers that should be visable
                
                
                if len(ir) < n_markers:
                    ir = None
#                if type(ir).__module__ != np.__name__:
#                    pdb.set_trace()
#                ir = ir.aslist()
            elif len(ir) < n_markers:
                ir = None
    
    len_ir = 0
    if ir != None:
        len_ir = len(ir)
        
    if len_ir != n_markers:
#        print("WARNING: {} markers found".format(len_ir))
        FOUND = False
    else: 
        FOUND = True
        
        
    if plot:
        
        
        if ir != None:
            
            for mark in ir:
                
                circle1 = plt.Circle(mark['pos'], mark['radius'] , color='b', fill = False, linewidth = 2)
                ax.add_artist(circle1)  
                
        else:
            len_ir = 0
        
        ax.set_title("N Markers: {}".format(len_ir))

        
                
        if FOUND:
#                 pass
            plt.savefig(".\\markers\\found\\{}\\frame_{}.png".format(plot_loc, it)) 
        else:
            plt.savefig(".\\markers\\not_found\\{}\\frame_{}.png".format(plot_loc, it)) 
        plt.close()
    
#    out = order_ir_markers(ir)
    
 
    
    return order_ir_markers(ir) #Order the markers and return
        
def gamma_correction(img, correction = 10):

    img = img/255.0
    img = cv2.pow(img, correction)
    return np.uint8(img*255)


def find_ir_markers_nofilt(frame, n_markers = 2, it = 0, tval = 150, gamma = None, plot_ax = None):
    """find all IR markers in a single frame. nofilt because it does not filter by any marker properties (e.g. Area, circularity)
    
    frame: numpy array of image
    n_markers: The number of IR markers that should be in image
    it: integer step counter. just for plotting/debugging
    
    To do:
        We need a smarter way of finding markers. The threshold and dilation/errosion may not account well for glare. 
        Glare leads to a large blob being found. In which case the threshold should increase (untill there are only 2 markers).
        Record lots of marker frames in various lighting conditions and work out what is a normal area of the actual markers (after checking that the true markers are being tracked)
    """
    

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) 
    
    if plot_ax != None:
        plot_ax[1].imshow(gray, cmap = "gray")
        
    if gamma != None:
            
        gray = gamma_correction(gray, correction = gamma)
        
        if plot_ax != None:
            plot_ax[2].imshow(gray, cmap = "gray")

     
#            plt.show()

    t_val = tval #Threshold value 
    t, thresh = cv2.threshold(gray, t_val, 255, cv2.THRESH_BINARY)
   
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, None)
#        thresh = cv2.erode(thresh, None, iterations = 2) #Are these necessary? Erode and dilate
#        thresh = cv2.dilate(thresh, None, iterations = 2)     
    
    if plot_ax != None:
            plot_ax[3].imshow(gray, cmap = "gray")
   
    cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]
    center = None    
    
    n_pos_markers = len(cnts) #Number of possible markers
  
    if n_pos_markers == 0:
        return None
    
    else:
    
        out = []
        
            
        for i in range(n_pos_markers):            
       
            c = cnts[i]
            ((x,y), radius) = cv2.minEnclosingCircle(c)
            M = cv2.moments(c)
            try:
                center = (int(M['m10'] / M['m00']), int(M['m01'] / M['m00']))
            except ZeroDivisionError:
                center = (x,y)
                
            compactness = np.square(cv2.arcLength(c, True)) / (4 * np.pi * cv2.contourArea(c))
#            print("Compactness: {}".format(compactness))
            dat = {'pos': (x,y), 'radius': radius, 'center': center, 'compactness': compactness}
            out.append(dat)                    
       

        return out #Return a list of dictionaries. One dict per marker
    
def order_ir_markers(markers):
    """Given a list of 2 IR markers (dicts) make the first item the left most marker. If None is passed also return None"""
    
  
    
    if markers == None:
        
        return None
        
    else:

        x_pos = np.array([i['pos'][0]  for i in markers]) #Get the x position of the markers
        
        left = x_pos.argmin()
        
        if left == 1:
            markers = markers[::-1]
            
        return markers

def markers2numpy(all_markers, n_markers = 2):
    """Takes a list of all markers in a video and converts the positions to a numpy array"""
    
    markers = np.empty((len(all_markers), n_markers, 2))
    
    for i in range(len(markers)):
        
        if all_markers[i] == None:
            markers[i] = np.NaN
            
        else:
            
            for j in range(len(markers[i])):
        
                markers[i,j] = all_markers[i][j]['pos'] 
    
    return markers
        
if __name__ == '__main__':
    
    jobs = multiprocessing.Queue(5)
    results = multiprocessing.Queue() #Queue to place the results into
    kill_confirmed = multiprocessing.Queue() #Debug queue to see why not being killed
    
    tmp = multiprocessing.Process(target = get_ir_marker_process, args=(jobs,results,kill_confirmed,))
    tmp.start()
    
    
    img = np.random.randint(0, 255, (1280, 720, 3))
    
    jobs.put([0, img])
    jobs.put("KILL")
    
    tmp.join()
    print("JOINED")
    
#    print(kill_confirmed.get())
