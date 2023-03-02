#!/usr/bin/env python3
import os
import pickle
from io import BytesIO
import cv2
import time
import numpy as np
import subprocess
import logging
import json
import sys
import paramiko
import pysftp

def main():
    import time as time1
    start = time1.time()
    cnopts = pysftp.CnOpts()
    cnopts.hostkeys = None
    try:

        sftp = pysftp.Connection(
            host="10.129.28.219", 
            username="faasapp",
            password="1234",
            cnopts=cnopts
        )
        logging.info("connection established successfully")
    except:
        logging.info('failed to establish connection to targeted server')

    edge_detect__directory = "edge-detected-images"
    is_edgedetect_dir = os.path.isdir(edge_detect__directory)
    if(is_edgedetect_dir == False):
        os.mkdir(edge_detect__directory)

    images_dir = "images"
    is_images_dir = os.path.isdir(images_dir)
    if(is_images_dir == False):
        os.mkdir(images_dir)

    
    remote_download_path = "/home/faasapp/Desktop/anubhav/sprocket-decode/"+images_dir

    remote_upload_path = "/home/faasapp/Desktop/anubhav/edge-detection/"+edge_detect__directory

    try:
        sftp.chdir(remote_download_path)  # Test if remote_path exists
    except IOError:
        sftp.mkdir(remote_download_path)  # Create remote_path
        sftp.chdir(remote_download_path)

    try:
        sftp.chdir(remote_upload_path)  # Test if remote_path exists
    except IOError:
        sftp.mkdir(remote_upload_path)  # Create remote_path
        sftp.chdir(remote_upload_path)

    sftp.get_d(remote_download_path,preserve_mtime=True,localdir=images_dir)

    activation_id = os.environ.get('__OW_ACTIVATION_ID')
    params = json.loads(sys.argv[1])
    
    decode_activation_id = params["activation_id"]
    decoded_images_sizes = {}
    edge_detected_images = {}
    parts = params["parts"]
    for i in range(0,parts):
        img_name = images_dir+'/Image' + str(i) + '.jpg'
        img =  cv2.imread(img_name)
        # height, width = img.shape[:2]
        size = os.stat(img_name).st_size
        decoded_images_sizes[img_name] = size
        image= cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        canny_output = cv2.Canny(image, 80, 150)

        filename = 'detected-edges-' + str(i) +'.jpg'
        # Saving the image
        cv2.imwrite(edge_detect__directory+"/"+filename, canny_output)

        edge_img = cv2.imread(edge_detect__directory+"/"+filename)
        # edge_height, edge_width = edge_img.shape[:2]

        edge_detected_size = os.stat(edge_detect__directory+"/"+filename).st_size
        edge_detected_images[edge_detect__directory+"/"+filename] = edge_detected_size
    
    current_path = os.getcwd()
    sftp.put_d(current_path+"/"+edge_detect__directory,preserve_mtime=True,remotepath=remote_upload_path)
    detected_edge_images = os.listdir(current_path+"/"+edge_detect__directory)
    end = time1.time()
    exec_time = end-start
    decode_execution_time = params["exec_time_decode"]
    print(json.dumps({ "edge_detection_output": detected_edge_images,
                        "edge_detect_activation_id": str(activation_id),
                        "number_of_images_processed": parts,
                        "edge_detection_execution_time": exec_time,
                        "decode_execution_time": decode_execution_time,
                        "edge_detected_images_size": edge_detected_images,
                        "decoded_images_size": decoded_images_sizes
                    }))
    

if __name__ == "__main__":
    main()