#!/usr/bin/env python3
import ffmpeg
import cv2
import time
from io import BytesIO
import os
import sys
import redis
import pickle
import json
from PIL import Image
import pysftp
import logging

logging.basicConfig(level=logging.INFO)

def main():
    print("Inside encode\n")
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


    filtered_dir = "filtered-images"
    is_images_dir = os.path.isdir(filtered_dir)
    if(is_images_dir == False):
        os.mkdir(filtered_dir)

    remote_path = "/home/faasapp/Desktop/anubhav/sprocket-filter/"+filtered_dir
    remote_upload_path = "/home/faasapp/Desktop/anubhav/sprocket-encode/"+filtered_dir
    try:
        sftp.chdir(remote_path)  # Test if remote_path exists
    except IOError:
        sftp.mkdir(remote_path)  # Create remote_path
        sftp.chdir(remote_path)

    try:
        sftp.chdir(remote_upload_path)  # Test if remote_path exists
    except IOError:
        sftp.mkdir(remote_upload_path)  # Create remote_path
        sftp.chdir(remote_upload_path)
    current_path = os.getcwd()

    sftp.get_d(remote_path,preserve_mtime=True,localdir=filtered_dir)
    
    sftp.put_d(current_path+"/"+filtered_dir,preserve_mtime=True,remotepath=remote_upload_path)

    # print("Current Path",current_path)
    
    path = current_path+"/"+filtered_dir+"/"

    output_path="output.avi"

    images = []

    input_images = os.listdir(path)

    for i in input_images:
        i=path+i
        images.append(i)

    images.sort()

    # cv2_fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    cv2_fourcc = cv2.VideoWriter_fourcc(*'MJPG')

    frame = cv2.imread(images[0])

    size = list(frame.shape)
    
    del size[2]
    size.reverse()
    video = cv2.VideoWriter("output.avi",cv2_fourcc,3,size,1)
    
    for i in range(len(images)):
        video.write(cv2.imread(images[i]))
        print('frame',i+1,'of',len(images))
   
    video.release()
   
    output_video_size = os.stat(output_path).st_size
    upload_path =  "/home/faasapp/Desktop/anubhav/sprocket-decode/output.avi"
    current_files = os.listdir('.')
    sftp.put(output_path,preserve_mtime=True,remotepath=upload_path)
    
    
    # r = redis.Redis(host="10.129.28.219", port=6379, db=2)
    
    activation_id = os.environ.get('__OW_ACTIVATION_ID')
    params = json.loads(sys.argv[1])
    decode_execution_time = params["exec_time_decode"]
    #print(decode_execution_time)
    filter_execution_time = params["exec_time_filter"]
    # print(filter_execution_time)
    parts = params["parts"]
    
    end = time1.time()

    exec_time = end-start
    total_time = decode_execution_time + filter_execution_time + exec_time
    print(json.dumps({ "encode_output": output_path,
                        "number_of_images_processed": parts,
                        "activation_id": str(activation_id),
                        "exec_time_filter": filter_execution_time,
                        "exec_time_decode": decode_execution_time,
                        "exec_time_encode": exec_time,
                        "workflow_execution_time": total_time,
                        "output_video_size_in_bytes": output_video_size
                        #"params":params
                    }))


if __name__ == "__main__":
    main()