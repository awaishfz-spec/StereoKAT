# -*- coding: utf-8 -*-
"""

About: A file ordering system for the postural control rig

Files should be stored in the following way

recorded_data
    Experiment_1
        Part1
            Recording 1
                3d_data.csv             (File containing the 3d positions, and summary metrics)
                ir_points.csv           (File containing IR points data)
                demographics.csv        (File containing participant demographics)
                notes.csv               (File containing notes about the recording)
                data_processing_log     (File showing the state of the data processing. For example this will flag if videos exist but 3d position data has not been logged)
                videos
                    server.h264         (raw video)
                    client.h264         (raw video)
            ...
            Recording 2
            Recording 3
        Part2
        Part3
    Experiment_N
"""
import shutil #For file moving
import os, sys
import glob
import pdb
import ir_marker

if getattr(sys, 'frozen', False):
   base_path = sys._MEIPASS   
else:   
   base_path = os.path.dirname(os.path.realpath(sys.argv[0]))

class FileOrderingSystem:
    """A class for controlling the postural cam file system"""
    
    def __init__(self, home_dir = None):

        if home_dir == None:
            
            self.home_dir = os.getcwd() #Parent directory of the Postural control project
            
        else:
            self.home_dir = home_dir
        
        print(os.getcwd())
#        assert self.home_dir == '/home/pi/Documents/Postural Control Project'
        
        self.recorded_data_dir = os.path.join(self.home_dir, 'recorded_data')
        
        
        self.check_recorded_dir_exists()
        
    def check_recorded_dir_exists(self):
        """Check the recorded_data director exists. If not create one"""
        
        recorded_dir_exists = os.path.isdir(self.recorded_data_dir)
        
        if not recorded_dir_exists:
            
            print("'recorded_data' directory does not exist. Creating it")
            print("Directory is: {}".format(self.recorded_data_dir))
            
            os.makedirs(self.recorded_data_dir)
        
        else:

            print("'recorded_data' directory exists")
            
            
            
    def find_participant_dir(self, demographics):
        """Check if a participant already has a directory. If not create one"""
        
        forename = demographics['forename']
        surname = demographics['surname']
        dob = demographics['DOB']        
        ID = demographics['ID']
        
       
        
        #If no ID the ID will become the initials and surname
        if ID == '':
            if len(forename) > 0:
                
                ID = forename[0] + surname
            
            else:
                ID = forename + surname
            
            
        print(ID)
        
        
        if ID == '':
            self.participant_dir = os.path.join(self.recorded_data_dir, 'DEBUG') #If no demographics has been entered save the data in the folder DEBUG
        
        else:
            self.participant_dir = os.path.join(self.recorded_data_dir, ID)        
        ###Check if directory exists
        
        part_dir_exists = os.path.isdir(self.participant_dir)
        
        if not part_dir_exists:
            
            os.makedirs(self.participant_dir)
            
            
    def find_participant_recording(self):
        """Check if any recordings have been made for this participant. If not create a new folder at ..0. If not start counting from last recording"""
        
        try: 
            self.participant_dir
            
        except NameError:
            
            raise NameError("Call find_participant_dir() before this function, to find the participant directory")
            
        
        Record_dirs = glob.glob(self.participant_dir+'/*') #Directories for all existing particpant records
        
        if Record_dirs == []:
            
            new_record_num = 0 #If not recordings yet start at 0
        
        else:
         
#            Records = [os.path.split(rec)[-1].split("_")[-1] for rec in Record_dirs] #Just get the file numbers
            
            Records = [os.path.split(rec)[-1] for rec in Record_dirs] 
            
            
            #If there are records in Records that start 'Record_' get the last record number (i.e Record_15). Else save data as 'Record_0'           
            Record_num = [int(rec.split("_")[-1]) for rec in Records if 'Record_' in rec]
            
            if len(Record_num) > 0:
                max_Records = max(Record_num) #Get the maximum record
        
                new_record_num = int(max_Records) + 1 #Go from last recording number
            
            else:
                
                new_record_num = 0
            
        self.recording_directory = os.path.join(self.participant_dir, 'Record_{}'.format(new_record_num)) #A directory for a specific record
        
        os.mkdir(self.recording_directory)
      

    def prep_record_directory(self):
         """Prep the record directory. If no video directory exists create one"""
         
         #Create video directory
         self.video_directory = os.path.join(self.recording_directory, 'videos')    

         if not os.path.isdir(self.video_directory):            
            os.mkdir(self.video_directory)
            
        #Create calibration directory
         self.calibration_directory = os.path.join(self.recording_directory, 'calibration')
        
         if not os.path.isdir(self.calibration_directory):             
             os.mkdir(self.calibration_directory)
            
    
    def move_files_to_record(self):    
        """Move all the files from the recording to the record file"""
        
        all_files = glob.glob(os.path.join(base_path, '*')) #Get all the files in the main directory
        print(all_files)
        
        server_video_fname = 'testIR_server.h264'
        client_video_fname = 'testIR.h264'
        
        server_timestamps_fname = 'time_stamps.csv'
        client_timestamps_fname = 'timestamps_server.csv'
        
        calibration_files = ['client_camera_calib_params.pkl', 'server_camera_calib_params.pkl', 'stereo_camera_calib_params.pkl']        
        
        
        if os.path.join(base_path, server_video_fname) in all_files:
            
            shutil.move(os.path.join(base_path, server_video_fname), os.path.join(self.video_directory, server_video_fname))

        if os.path.join(base_path, client_video_fname) in all_files:

                      
            shutil.move(os.path.join(base_path, client_video_fname), os.path.join(self.video_directory, client_video_fname))

        
        if os.path.join(base_path, server_timestamps_fname) in all_files:
            
            shutil.move(os.path.join(base_path, server_timestamps_fname), os.path.join(self.recording_directory, server_timestamps_fname))
 
            
        if os.path.join(base_path, client_timestamps_fname) in all_files:
            
            shutil.move(os.path.join(base_path, client_timestamps_fname), os.path.join(self.recording_directory, client_timestamps_fname))         

        #Copy the calibration files over
        
        for cal in calibration_files:
            
            shutil.copy(os.path.join(base_path, 'calibration', cal), self.calibration_directory) #Move all files to a calibration directory folder 
        
    def check_record_process_status(self, record_fname = None):
        """Check the process status of a directory or record
        
                3d_data.csv             (File containing the 3d positions, and summary metrics)
                ir_points.csv           (File containing IR points data)
                demographics.csv        (File containing participant demographics)
                notes.csv               (File containing notes about the recording)
                data_processing_log     (File showing the state of the data processing. For example this will flag if videos exist but 3d position data has not been logged)
                videos
                    server.h264         (raw video)
                    client.h264         (raw video)
        """
        
        if record_fname == None:
            
            record_fname = self.recording_directory #If a record directory is not provided make it the record specified by self 
            
        
        directory_files = glob.glob(os.path.join(record_fname, '*'))
        directory_files = [os.path.split(f)[-1] for f in directory_files] #Get just the file names
        
        video_files = [os.path.split(f)[-1] for f in glob.glob(os.path.join(record_fname, 'videos', '*'))]
        expected_files = ['summary.csv', 'demographics.csv', 'notes.csv']
        expected_videos = ['testIR.h264', 'testIR_server.h264']
        
        processed_files = {}
        
        for file in expected_files:
            
            if file in directory_files:
                processed_files[file] = True
            else:
                processed_files[file] = False
                
        for vid in expected_videos:
            
            if vid in video_files:
                processed_files[vid] = True
            else:
                processed_files[vid] = False
        
        
        return processed_files
            
    def check_directory_status(self, data_directory):
        
        """DEPRECIATED
        Return the number of files that are unprocessed in a directory.
        The directory should be the experiment level directory
        
        """        
        
        n_proc = 0
        unprocessed_directories = [] #List of directories that need processing
        all_participant_directories = glob.glob(data_directory+'*')
        
        for part in all_participant_directories:
            
            all_part_records = glob.glob(os.path.join(part, '*')) #All the records for this participant
            
            for rec in all_part_records:
            
                rec_status = self.check_record_process_status(rec)
            
                if rec_status['3d_data.csv'] == False:
                    
                    n_proc += 1
                
                    unprocessed_directories.append(rec)
        
        print("There are {} files to process".format(n_proc))
        
        return n_proc, unprocessed_directories
        

        
        
    def process_directory(self, unprocessed_directories):
        """Process all the files in a directory. Use threads or multiprocess to run the marker processing in parallel"""
        
        for directory in unprocessed_directories:
            
            client_vid_fname = os.path.join(directory, 'videos', 'testIR.h264')
            server_vid_fname = os.path.join(directory, 'videos', 'testIR_server.h264')
                   
        
            proc = posturalProc(v_fname = 'testIR.h264', kind = 'client')
            proc2 = posturalProc(v_fname = 'testIR_server.h264', kind = 'client')
            

            markersa = proc.get_ir_markers()    
            markersb = proc.get_ir_markers()
            
            markersa = ir_marker.markers2numpy(markersa)
            markersb = ir_marker.markers2numpy(markersb)
            
        
            
      
##
#    proc_all_markers = markers2numpy(proc.get_ir_markers())
#    proc2_all_markers = markers2numpy(proc2.get_ir_markers())[:proc_all_markers.shape[0]]
#    
#    stereo =  stereo_process(proc, proc2)
#        
#    markers3d = stereo.triangulate_all_get_PL(proc_all_markers, proc2_all_markers) #Get the marker positions in 3d space   
#    
#    markers3d_filt = stereo.kalman_smoother(markers3d)
#    
#    markers3d_filt[np.isnan(markers3d)] = np.NaN #Make values where no data was recorded NaN
#    
#    
#    distance_between_leds = np.sqrt(np.sum(np.square(np.diff(markers3d, axis = 1)), axis = 2)).squeeze()
#    distance_between_leds_filt = np.sqrt(np.sum(np.square(np.diff(markers3d_filt, axis = 1)), axis = 2)).squeeze()
#    
#   
#    
        
        
if __name__ == '__main__':
    
    fos = FileOrderingSystem('F:\\ogtestPSAT\\')
    
    demographics = {'forename': 'Oscar', 'surname': 'Giles', 'DOB': '29/07/1990', 'ID': 'P01'}
    
    fos.find_participant_dir(demographics) #Call this to check the participant directory exists. If not make one
    fos.find_participant_recording()
    fos.prep_record_directory()
    
    fos.move_files_to_record()
#    
#    a= fos.check_record_process_status('F:\\Postural Control Project\\recorded_data\\ExpOne\\OGiles\\Record_0\\')
#    direct = 'H:\\Postural Control Project osc\\Postural Control Project\\recorded_data\\'
    
#    N, dirs = fos.check_directory_status(direct)
