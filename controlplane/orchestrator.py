#!/usr/bin/env python3

import sys
import requests
import uuid
import re
import subprocess
import threading
import queue
import redis
from flask import current_app
import pickle
import json
import os
import time
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from flask import Flask, request,jsonify,send_file
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
import pymongo


# app = Flask(__name__)

action_url_mappings = {} #Store action->url mappings
action_properties_mapping = {} #Stores the action name and its corresponding properties
responses = []
queue = []
list_of_func_ids = [] 
dag_responses = []

x = 10


def preprocess(filename):
    with open(filename) as f:
        lines = f.readlines()
    action_url_list = []
    for line in lines:
        line = line.replace("\n", "")
        line = line.replace("/guest/","")
        action_url_list.append(line)
    for item in action_url_list:
        action_name = item.split(' ')[0]
        url = item.split(' ')[1]
        action_url_mappings[action_name] = url


def execute_thread(action,redis,url,json):
    reply = requests.post(url = url,json=json,verify=False)
    list_of_func_ids.append(reply.json()["activation_id"])
    redis.set(action+"-output",pickle.dumps(reply.json()))
    responses.append(reply.json())
    

def handle_parallel(queue,redis,action_properties_mapping,parallel_action_list):
    thread_list = []
    output_list = [] # List to store the output of actions whose outputs are required by downstream operations
    
    for action in parallel_action_list:
        action_names = action_properties_mapping[action]["outputs_from"]
        next_action = action_properties_mapping[action]["next"]
        if(next_action!=""):
            if next_action not in queue:
                queue.append(next_action)
        if(len(action_names)==1): # if only output of one action is required
            key = action_names[0]+"-output"
            output = pickle.loads(redis.get(key))
            action_properties_mapping[action]["arguments"] = output
        else:
            for item in action_names:
                key = item+"-output"
                output = pickle.loads(redis.get(key))
                output_list.append(output)
            
            action_properties_mapping[action]["arguments"] = output_list
        
        url = action_url_mappings[action]
        thread_list.append(threading.Thread(target=execute_thread, args=[action,redis,url,action_properties_mapping[action]["arguments"]]))
    for thread in thread_list:
        thread.start()
    for thread in thread_list:
        thread.join()
    action_properties_mapping[next_action]["arguments"] = responses
    return responses

def create_redis_instance():
    r = redis.Redis(host="10.129.28.219", port=6379, db=2)
    return r


def get_dag_json(dag_name):
    myclient = pymongo.MongoClient("mongodb://127.0.0.1/27017")
    mydb = myclient["dag_store"]
    mycol = mydb["dags"]
    query = {"name":dag_name}
    projection = {"_id": 0, "name": 1,"dag":1}
    document = mycol.find(query, projection)
    data = list(document)
    return data

def submit_dag_metadata(dag_metadata):
    myclient = pymongo.MongoClient("mongodb://127.0.0.1/27017")
    mydb = myclient["dag_store"]
    mycol = mydb["dag_metadata"]
    try:
        cursor = mycol.insert_one(dag_metadata)
        # print("OBJECT ID GENERATED",cursor.inserted_id)
        data = {"message":"success"}
        return json.dumps(data)
    except Exception as err:
        data = {"message":"failed","reason":err}
        return json.dumps(data)



def execute_action(action_name):
    script_file = './actions.sh'
    subprocess.call(['bash', script_file])
    preprocess("action_url.txt")
    url = action_url_mappings[action_name]
    # print(request.json)
    # json_data = json.loads(request.json)
    reply = requests.post(url = url,json = request.json,verify=False)
    return reply.json()


    
def execute_dag(dag_name):
    
    print("------------------------------------DAG START-----------------------------------------------")
    unique_id = uuid.uuid4()
    print("DAG UNIQUE ID----------",unique_id)
    dag_metadata={}
    dag_metadata["dag_id"] = str(unique_id)
    dag_metadata["dag_name"] = dag_name
    list_of_func_ids = []
    ######### Updates the list of action->url mapping ###################
    script_file = './actions.sh'
    subprocess.call(['bash', script_file])
    #####################################################################
    preprocess("action_url.txt")

    ### Create in-memory redis storage ###
    redis_instace = create_redis_instance()
    #######################################

    action_properties_mapping = {} #Stores the action name and its corresponding properties
    

    dag_res = json.loads(json.dumps(get_dag_json(dag_name)))
    dag_data = dag_res[0]["dag"]
    for dag_item in dag_data:
        action_properties_mapping[dag_item["node_id"]] = dag_item["properties"]
    
    flag = 0
    for dag_item in dag_data:
        if(flag==0): # To indicate the first action in the DAG
            queue.append(dag_item["node_id"])
            action_properties_mapping[dag_item["node_id"]]["arguments"] = request.json
        while(len(queue)!=0):
            flag=flag+1
            action = queue.pop(0)
            print("ACTION DEQUEUED FROM QUEUE : --->",action)
            ##########################################################
            #               HANDLE THE ACTION                        #
            ##########################################################
            if isinstance(action, str):
                # if(isinstance(action_properties_mapping[action]['arguments'],list)):
                #     pass
                json_data = action_properties_mapping[action]["arguments"]
                url = action_url_mappings[action]
                reply = requests.post(url = url,json=json_data,verify=False)
                list_of_func_ids.append(reply.json()["activation_id"])
                # print("Line 292------------",reply.json()["activation_id"])
                redis_instace.set(action+"-output",pickle.dumps(reply.json()))
                action_type = action_properties_mapping[action]["primitive"]
                
                if(action_type=="condition"):
                    branching_action = action_properties_mapping[action]["branch_1"]
                    alternate_action = action_properties_mapping[action]["branch_2"]
                    result=reply.json()["result"]
                    condition_op = action_properties_mapping[action]["condition"]["operator"]
                    if(condition_op=="equals"):
                        if(isinstance(action_properties_mapping[action]["condition"]["target"], str)):
                            target = action_properties_mapping[action]["condition"]["target"]
                        else:
                            target=int(action_properties_mapping[action]["condition"]["target"])

                        if(result==target):
                            output_list = [] # List to store the output of actions whose outputs are required by downstream operations
                            queue.append(branching_action)
                            action_names = action_properties_mapping[branching_action]["outputs_from"] # Get the list of actions whose output will be used
                            if(len(action_names)==1): # if only output of one action is required
                                key = action_names[0]+"-output"
                                output = pickle.loads(redis_instace.get(key))
                                action_properties_mapping[branching_action]["arguments"] = output
                            else:
                                for item in action_names:
                                    key = item+"-output"
                                    output = pickle.loads(redis_instace.get(key))
                                    output_list.append(output)
                                action_properties_mapping[branching_action]["arguments"] = output_list
                            
                        else:
                            output_list = [] # List to store the output of actions whose outputs are required by downstream operations
                            queue.append(alternate_action)
                            action_names = action_properties_mapping[alternate_action]["outputs_from"] # Get the list of actions whose output will be used
                            if(len(action_names)==1): # if only output of one action is required
                                key = action_names[0]+"-output"
                                output = pickle.loads(redis_instace.get(key))
                                action_properties_mapping[alternate_action]["arguments"] = output
                            else:
                                for item in action_names:
                                    key = item+"-output"
                                    output = pickle.loads(redis_instace.get(key))
                                    output_list.append(output)
                                action_properties_mapping[alternate_action]["arguments"] = output_list

                            
                    if(condition_op=="greater_than"):
                        pass 
                    if(condition_op=="greater_than_equals"):
                        pass
                    if(condition_op=="less_than"):
                        pass
                    if(condition_op=="less_than_equals"):
                        pass
                elif(action_type=="serial"):
                    next_action = action_properties_mapping[action]["next"]
                    if(next_action!=""):
                        output_list = [] # List to store the output of actions whose outputs are required by downstream operations
                        queue.append(next_action)
                        action_names = action_properties_mapping[next_action]["outputs_from"] # Get the list of actions whose output will be used
                        if(len(action_names)==1): # if only output of one action is required
                            key = action_names[0]+"-output"
                            output = pickle.loads(redis_instace.get(key))
                            action_properties_mapping[next_action]["arguments"] = output
                        else:
                            for item in action_names:
                                key = item+"-output"
                                output = pickle.loads(redis_instace.get(key))
                                output_list.append(output)
                            action_properties_mapping[next_action]["arguments"] = output_list

                elif(action_type=="parallel"):
                    parallel_action_list = action_properties_mapping[action]["next"]
                    queue.append(parallel_action_list)
                    
                    
            else:
                reply = handle_parallel(queue,redis_instace,action_properties_mapping,action)
                

                
                    
    dag_metadata["function_activation_ids"] = list_of_func_ids       
    # print("DAG SPEC AFTER WORKFLOW EXECUTION--------\n")
    # print(action_properties_mapping)
    # print('\n')
    submit_dag_metadata(dag_metadata)
    print("DAG ID---->FUNC IDS",dag_metadata)
    print('\n')
    # print('INTERMEDIATE OUTPUTS FROM ALL ACTIONS-----\n')
    # get_redis_contents(redis_instace)
    # print('\n')
    redis_instace.flushdb()
    print("Cleaned up in-memory intermediate outputs successfully\n")
    
    if(isinstance(reply,list)):
        res = {"dag_id": dag_metadata["dag_id"],
                "result": reply
            }
    else:
        res = { 
                "dag_id": dag_metadata["dag_id"],
                "result": reply.json()
            }
    
    dag_responses.append(res)
        
        