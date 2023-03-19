#!/usr/bin/env python3

import sys
import requests
import uuid
import re
import subprocess
import threading
import queue
import redis
import pickle
import json
import os
import time
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from flask import Flask, request,jsonify,send_file
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
import pymongo
import shutil

import trigger_gateway


app = Flask(__name__)

action_url_mappings = {} #Store action->url mappings
action_properties_mapping = {} #Stores the action name and its corresponding properties
responses = []
queue = []
list_of_func_ids = [] 

def hello():
    print("Hello")


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

def get_redis_contents(r):
    keys = r.keys()
    for key in keys:
        value = pickle.loads(r.get(key))
        if value is not None:
            print(f"{key.decode('utf-8')}: {json.dumps(value, indent=4)}")

def connect_mongo():
    myclient = pymongo.MongoClient("mongodb://127.0.0.1/27017")
    mydb = myclient["dag_store"]
    mycol = mydb["dags"]
    return mycol

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

@app.route("/")
def home():
    data = {"message": "Hello,welcome to create and manage serverless workflows.","author":"Anubhav Jana"}
    return jsonify(data)

@app.route('/view/functions', methods=['GET'])
def list_actions():
    list_of_actions = []
    stream = os.popen(' wsk -i action list')
    actions = stream.read().strip().split(' ')
    for action in actions:
        if action=='' or action=='private' or action=='blackbox':
            continue
        else:
            list_of_actions.append(action.split('/')[2])
    data = {"list of available actions":list_of_actions}
    return jsonify(data)



@app.route('/register/trigger/',methods=['POST'])
def register_trigger():
    trigger_json = request.json
    myclient = pymongo.MongoClient("mongodb://127.0.0.1/27017")
    mydb = myclient["trigger_store"]
    mycol = mydb["triggers"]
    try:
        cursor = mycol.insert_one(trigger_json)
        print("OBJECT ID GENERATED",cursor.inserted_id)
        if(trigger_json["type"]=="dag"):
            targets = trigger_json["dags"]
        elif(trigger_json["type"]=="function"):
            targets = trigger_json["functions"]
        data = {"message":"success","trigger_name":trigger_json["trigger_name"],"trigger":trigger_json["trigger"],"trigger_type":trigger_json["type"],"trigger_target":targets}
        return json.dumps(data)
    except Exception as e:
        print("Error--->",e)
        data = {"message":"fail","reason":e}
        return json.dumps(data)


@app.route('/register/function/<function_name>',methods=['POST'])
def register_function(function_name):
    list_of_file_keys = []
    document = {}
    function_dir = '/home/faasapp/Desktop/anubhav/function_modules' # Library of functions
    new_dir = function_name
    destination = os.path.join(function_dir, new_dir)
    # Create the directory
    os.makedirs(destination, exist_ok=True)
    files = request.files
    for filekey in files:
        if filekey!='description':
            list_of_file_keys.append(filekey)
    for key in list_of_file_keys:
        file = request.files[key]
        filename = file.filename
        # Save, copy, remove
        file.save(file.filename)
        shutil.copy(filename, destination)
        os.remove(filename)
    image_build_script = 'buildAndPush.sh'
    shutil.copy(image_build_script, destination)
    
    # Prepare data 
    document["function_name"] = function_name
    document["image_build_script"] = 'buildAndPush.sh'
    document["python_script"] = (request.files[list_of_file_keys[0]]).filename
    document["dockerfile"] = (request.files[list_of_file_keys[1]]).filename
    document["requirements.txt"] =(request.files[list_of_file_keys[2]]).filename

    docker_image_name = "10.129.28.219:5000/"+function_name+"-image"
    api_name = "/"+function_name+"-api"
    path_name = "/"+function_name+"-path"
    password = '1234'
    # build docker image
    cmd = ["sudo", "-S", "/home/faasapp/Desktop/anubhav/controlplane/build_image.sh",destination,docker_image_name]
    # open subprocess with Popen
    process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

    # pass password to standard input
    process.stdin.write(password + "\n")
    process.stdin.flush()

    # wait for process to complete and get output
    output, errors = process.communicate()
    print("OUTPUT---------",output)
    print("ERRORS---------",errors)
    # if(errors):
    #     print("There is error building docker file")
    #     data = {"message":"fail","reason":"docker build failed"}
    #     return json.dumps(data)
    # else:

        # create action, register action with api, populate its mapping
    subprocess.call(['./create_action.sh',destination,docker_image_name,function_name])
    subprocess.call(['./register.sh',api_name,path_name,function_name])
    subprocess.call(['bash', './actions.sh'])
    
    myclient = pymongo.MongoClient("mongodb://127.0.0.1/27017")
    mydb = myclient["function_store"]
    mycol = mydb["functions"]
    try:
        cursor = mycol.insert_one(document)
        print("OBJECT ID GENERATED",cursor.inserted_id)
        data = {"message":"success"}
        return json.dumps(data)
    except Exception as e:
        print("Error--->",e)
        data = {"message":"fail","reason":e}
        return json.dumps(data)

        # data = {"message":"success"}
        # return json.dumps(data)


@app.route('/register/dag/',methods=['POST'])
def register_dag():
    dag_json = request.json
    myclient = pymongo.MongoClient("mongodb://127.0.0.1/27017")
    mydb = myclient["dag_store"]
    mycol = mydb["dags"]
    try:
        cursor = mycol.insert_one(dag_json)
        print("OBJECT ID GENERATED",cursor.inserted_id)
        data = {"message":"success"}
        return json.dumps(data)
    except Exception as e:
        print("Error--->",e)
        data = {"message":"fail","reason":e}
        return json.dumps(data)

@app.route('/view/dag/<dag_name>',methods=['GET'])
def view_dag(dag_name):
    dag_info_map = {}
    myclient = pymongo.MongoClient("mongodb://127.0.0.1/27017")
    mydb = myclient["dag_store"]
    mycol = mydb["dags"]
    document = mycol.find({"name":dag_name})
    data = list(document)
    dag_info_list = []
    for items in data:
        dag_info_list = items["dag"]
        dag_info_map["DAG_Name--->>"] = items["name"]
    
    dag_info_map["Number_of_nodes-->"] = len(dag_info_list)
    dag_info_map["Starting_Node-->"] = dag_info_list[0]["node_id"]

    for dag_items in dag_info_list:
        node_info_map = {}
        if(len(dag_items["properties"]["outputs_from"])==0):
            node_info_map["get_outputs_from-->"] = "Starting action->No outputs consumed"
        else:
            node_info_map["get_outputs_from-->"] = dag_items["properties"]["outputs_from"]
        node_info_map["primitive_type"] = dag_items["properties"]["primitive"]
        if(dag_items["properties"]["primitive"]=="condition"):
            node_info_map["next_node_id_if_condition_true"] = dag_items["properties"]["branch_1"]
            node_info_map["next_node_id_if_condition_false"] = dag_items["properties"]["branch_2"]
        else:
            if(dag_items["properties"]["next"]!=""):
                node_info_map["next_node_id-->"] = dag_items["properties"]["next"]
            else:
                node_info_map["next_node_id-->"] = "Ending node_id of a path"
        dag_info_map[dag_items["node_id"]] = node_info_map
    response = {"dag_data":dag_info_map}
    formatted_json = json.dumps(response, indent=20)
    return formatted_json

@app.route('/view/dags',methods=['GET'])
def view_dags():
    myclient = pymongo.MongoClient("mongodb://127.0.0.1/27017")
    mydb = myclient["dag_store"]
    mycol = mydb["dags"]
    document = mycol.find()
    data = list(document)
    # Serialize the data to JSON
    json_data = json.dumps(data, default=str)
    json_string ='{"dag":'+str(json_data)+'}'
    data = json.loads(json_string)
    # Format the JSON string with indentation
    formatted_json = json.dumps(data, indent=4)
    return formatted_json

@app.route('/view/triggers',methods=['GET'])
def view_triggers():
    myclient = pymongo.MongoClient("mongodb://127.0.0.1/27017")
    mydb = myclient["trigger_store"]
    mycol = mydb["triggers"]
    document = mycol.find()
    data = list(document)
    # Serialize the data to JSON
    json_data = json.dumps(data, default=str)
    json_string ='{"trigger":'+str(json_data)+'}'
    data = json.loads(json_string)
    # Format the JSON string with indentation
    formatted_json = json.dumps(data, indent=4)
    return formatted_json

@app.route('/view/trigger/<trigger_name>',methods=['GET'])
def view_trigger(trigger_name):
    print(request.url)
    myclient = pymongo.MongoClient("mongodb://127.0.0.1/27017")
    mydb = myclient["trigger_store"]
    mycol = mydb["triggers"]
    query = {"trigger_name":trigger_name}
    projection = {"_id": 0,"trigger_name":1,"type":1,"trigger":1,"dags":1,"functions":1}
    document = mycol.find(query,projection)
    data = list(document)
    # print(data)
    json_data = json.dumps(data, default=str)
    json_string ='{"trigger":'+str(json_data)+'}'
    data = json.loads(json_string)
    formatted_json = json.dumps(data, indent=4)
    return formatted_json
    
# EXAMPLE URL: http://10.129.28.219:5001/view/activation/8d7df93e8f2940b8bdf93e8f2910b80f
@app.route('/view/activation/<activation_id>', methods=['GET', 'POST'])
def list_activations(activation_id):
    # activation_id = '74a7b6c707d14973a7b6c707d1a97392'
    cmd = ['wsk', '-i', 'activation', 'get', activation_id]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    json_res = result.stdout.decode().split('\n')[1:] # Ignore first line of output
    res = json.loads('\n'.join(json_res))
    d={}
    d["action_name"] = res["name"]
    d["duration"] = res["duration"]
    d["status"] = res["response"]["status"]
    d["result"] = res["response"]["result"]
    return({"action_name":res["name"],
            "duration": res["duration"],
            "status": res["response"]["status"],
            "result":res["response"]["result"]
        })

# EXAMPLE URL: http://10.129.28.219:5001/view/76cc8a53-0a63-47bb-a5b5-9e6744f67c61
@app.route('/view/<dag_id>',methods=['GET'])
def view_dag_metadata(dag_id):
    myclient = pymongo.MongoClient("mongodb://127.0.0.1/27017")
    mydb = myclient["dag_store"]
    mycol = mydb["dag_metadata"]
    query = {"dag_id":dag_id}
    projection = {"_id": 0,"dag_id":1,"dag_name":1,"function_activation_ids":1}
    document = mycol.find(query, projection)
    data = list(document)
    response = {"dag_metadata":data}
    return json.dumps(response)

# EXAMPLE URL: http://10.129.28.219:5001/run/action/odd-even-action
# http://10.129.28.219:5001/run/action/decode-function

@app.route('/run/action/<action_name>/', methods=['POST'])
def execute_action(action_name):
    script_file = './actions.sh'
    subprocess.call(['bash', script_file])
    preprocess("action_url.txt")
    url = action_url_mappings[action_name]
    # json_data = json.loads(request.json)
    reply = requests.post(url = url,json = request.json,verify=False)
    return reply.json()


    
# EXAMPLE URL: http://10.129.28.219:5001/run/dag/odd-even-test/{"number":16}
@app.route('/run/dag/<dag_name>/', methods=['GET', 'POST'])
def execute_dag(dag_name):
    print("------------------------------------DAG START-----------------------------------------------")
    unique_id = uuid.uuid4()
    print("DAG UNIQUE ID----------",unique_id)
    dag_metadata={}
    dag_metadata["dag_id"] = str(unique_id)
    dag_metadata["dag_name"] = dag_name
    # list_of_func_ids = []
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
    # print("DAG ID---->FUNC IDS",dag_metadata)
    print('\n')
    # print('INTERMEDIATE OUTPUTS FROM ALL ACTIONS-----\n')
    # get_redis_contents(redis_instace)
    # print('\n')
    redis_instace.flushdb()
    print("Cleaned up in-memory intermediate outputs successfully\n")
    
    if(isinstance(reply,list)):
        return({"dag_id": dag_metadata["dag_id"],
                "result": reply
            })

    else:
        return({ 
                "dag_id": dag_metadata["dag_id"],
                "result": reply.json()
            })
    # return({ 
    #             "result": "success"
    #         })




if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)

