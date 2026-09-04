# -*- coding: utf-8 -*-
"""
A simple script to connect to a raspberry pi and ask for it's IP address using paramiko
"""
import paramiko


class shh_client:
    
    def __init__(self):
        
        self.connect() #Try to connect to RPi Server
        
        
    def connect(self):
        
        try:
            self.shh = paramiko.SSHClient()
            self.shh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            addr = '192.168.0.3'
            username = 'pi'
            password = 'raspberry'
            print("Attempting to establist connection")
            self.shh.connect(addr, username = username,  password = password )
            print("Connection established")
        except:
            print("Unable to establish a connection")
            
    def ask_hostname(self):
        """Ask the RPI Server to start running a server file"""
        
        stdin, stdout, stderror = self.shh.exec_command("hostname -I")

        print(stdout.readlines())

    def start_server(self):

        #stdin, stdout, stderror = self.shh.exec_command("cd ~/Documents/PostureTracker_Project")
        stdin, stdout, stderror = self.shh.exec_command("python3 Documents/PSAT_Server/posturalCam_master_NETWORK.py")

    def shutdown_server_pi(self):

        stdin, stdout, stderror = self.shh.exec_command("sudo shutdown now")

        print("stdout: {}\nstderror: {}".format(stdout.readlines(), stderror.readlines()))

    def send_command(self, cmd):

        stdin, stdout, stderror = self.shh.exec_command(cmd)

        print("stdout: {}\nstderror: {}".format(stdout.readlines(), stderror.readlines()))

if __name__ == '__main__':
    
    my_shh = shh_client()
    
    my_shh.ask_hostname()
    my_shh.start_server()
