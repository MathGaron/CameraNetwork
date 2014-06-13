#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Fri May 23 14:27:55 2014

@author: mathieugaron
"""


import os
import time
import actionlib

import roslib; roslib.load_manifest('camera_controler')
import rospy
from camera_network_msgs.msg import *

import paramiko


class sftp_server:
    
    def __init__(self,imagePath):
        self.imagePath = imagePath
        self.dateFolder = ''
        self.localImagePath = self.imagePath + self.dateFolder
        self.localLogPath = self.imagePath + 'log/'
        self.fileQty = 0
        
        rospy.loginfo('Writing files to ' + self.localImagePath)
        rospy.loginfo('Wrinting log to ' + self.localLogPath)
        rospy.loginfo('Setting up sftp Server')
        
        self.server = actionlib.SimpleActionServer('sftp',CameraDownloadAction,
                                                   self.execute,False)
        self.server.start()
        
        self.ipDict = {}
        
        if not os.path.exists(self.localLogPath):
            os.makedirs(self.localLogPath)
 
        # setup logging
        paramiko.util.log_to_file(self.localLogPath + time.strftime('%d%B%Hh') + '.log')

    def execute(self,goal):
        hz = 0
        totalCount = 0
        try:
            hz = 1/goal.dowload_frequency_s
            rospy.loginfo("Downloading at a rate of "+str(hz)+" hz")
        except ZeroDivisionError:
            hz = 1            
            rospy.loginfo("Instant Download")
            
        r = rospy.Rate(hz)
        while True:
            self.refresh_ip()
            self.refresh_date()
            
            pictureQty = self.download_all_images_from_network()
            totalCount += pictureQty
            if self.server.is_preempt_requested() or goal.dowload_frequency_s == 0:
                break
            r.sleep()
        succes_msg = CameraDownloadActionResult
        succes_msg.total_downloaded = 'Downloaded ' + str(totalCount) + ' pictures from ' + str(len(self.ipDict)) + ' devices.'

        self.server.set_succeeded(succes_msg)
        

    def refresh_ip(self):
        self.ipDict = rospy.get_param('/IP',{})
        rospy.loginfo("refreshing ip dic" + str(self.ipDict))
        
    def refresh_date(self):
        self.dateFolder = time.strftime("%B") + '/'
        self.localImagePath = self.imagePath + self.dateFolder
        

    def download_all_images_from_network(self):
        """
        Open sftp session to download images of each session
        return a tuple of number of device and total transfered images
        """
        imageQty = 0
        for name,ip in self.ipDict.items():
            try:
                rospy.loginfo('start sftp session with '+ name + ' on ip ' + ip + ' and port 22')
                sftp,t = self._createSession(ip)
                imageQty += self._downloadImageFolder(sftp,name)
                
                t.close()
                rospy.loginfo('Session with ' + ip + ' closed')


            except Exception as e:
                rospy.logwarn('*** Caught exception: %s: %s' % (e.__class__, e))
                try:
                    t.close()
                except:
                    pass
        return imageQty
    
    def _createSession(self,ip,port=22):
         t = paramiko.Transport((ip, port))
         t.connect(username='pi', password='raspberry')
         sftp = paramiko.SFTPClient.from_transport(t)
         return (sftp,t)
               
    def _downloadImageFolder(self,sftp,deviceName=''):
        feedback_msg = CameraDownloadActionFeedback
        filelist = sftp.listdir('.' + self.imagePath + self.dateFolder)
        rospy.loginfo('found ' + str(len(filelist)) + ' files')
                
                
        if not os.path.exists(self.localImagePath + deviceName):
            os.makedirs(self.localImagePath + deviceName)
        count = 1.0;                     
        if len(filelist) == 0:
            rospy.loginfo("No file to download")
        else:
            for f in filelist:
                rospy.loginfo('Downloading ' + f)
                remoteFile = '.' + self.imagePath + self.dateFolder + f
                localFile = self.localImagePath + deviceName + '/' + f
                sftp.get(remoteFile,localFile)
                sftp.remove(remoteFile)
                feedback_msg.picture_downloaded = str(float(count/len(filelist)*100)) + '% of Device ' + deviceName
                self.server.publish_feedback(feedback_msg)
                count += 1;
        return len(filelist)
        
    

if __name__ == "__main__":
    rospy.init_node('sftp_server')
    sftp = sftp_server()
    rospy.spin()

