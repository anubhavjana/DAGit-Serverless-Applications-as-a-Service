
import requests
import sys
import json
import pymongo

def get_trigger():
    myclient = pymongo.MongoClient("mongodb://127.0.0.1/27017")
    mydb = myclient["trigger_store"]
    mycol = mydb["triggers"]
    # query = {"dag_id":dag_id}
    projection = {"_id": 0,"trigger_name":1,"type":1,"trigger":1,"dags":1,"functions":1}
    document = mycol.find()
    data = list(document)
    print(data)
    json_data = json.dumps(data, default=str)
    json_string ='{"trigger_data":'+str(json_data)+'}'
    data = json.loads(json_string)
    # Format the JSON string with indentation
    formatted_json = json.dumps(data, indent=4)
    return formatted_json

    
def main():
    res = json.loads(get_trigger())
    print(res)


# def server():
#     # server_ip = "10.129.28.219"
#     # server_port = "5001"
#     url = "http://10.129.28.219:5001/register/trigger/myfirsttrigger"
#     # data = {"trigger_name":"myfirsttrigger", "dags":['odd-even-test']}
#     # json_data = json.dumps(data)
#     input_json_file = open(sys.argv[1])
#     params = json.load(input_json_file)
#     reply = requests.post(url = url,json = params,verify=False)
#     print(reply.json())
   

# def main():
#     server()

if __name__=="__main__":
    main()



