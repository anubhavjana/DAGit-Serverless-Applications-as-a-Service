import requests
import threading
import os
import json
import sys
import requests
import torch
from PIL import Image
from transformers import BlipProcessor, BlipForConditionalGeneration
thread_list = []
results = []

def process(image_url):
    processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
    model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
    # img_url = 'https://storage.googleapis.com/sfr-vision-language-research/BLIP/demo.jpg' 
    raw_image = Image.open(requests.get(image_url, stream=True).raw).convert('RGB')
    inputs = processor(raw_image, return_tensors="pt")
    out = model.generate(**inputs)
    result = processor.decode(out[0], skip_special_tokens=True)
    results.append(result)
def main(params):
    activation_id = os.environ.get('__OW_ACTIVATION_ID')
    # file = open('action/1/bin/exec__.py', 'r')
    # content = file.read()
    # print(content)
    print("Current directory----",os.getcwd())
    print("root----",os.listdir('/'))
    print("inside action----",os.listdir('/action/models/transformers'))
    print("current directory contents------",os.listdir(os.getcwd()))
    # print("/action/model contents------",os.listdir('../models/transformers'))
    
    # print("action/1/bin------",os.listdir('/action/1/bin'))
    

    # params = json.loads(sys.argv[1])
    img_urls = params["image_url_links"]

    modelpath = '/action/models/transformers'
    
    # print("Line 32------",os.listdir(model_path))
    
    # processor = BlipProcessor.from_pretrained(modelpath)
    # model = BlipForConditionalGeneration.from_pretrained(modelpath)
    processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
    model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
    img_url = 'https://storage.googleapis.com/sfr-vision-language-research/BLIP/demo.jpg' 
    raw_image = Image.open(requests.get(img_url, stream=True).raw).convert('RGB')
    inputs = processor(raw_image, return_tensors="pt")
    out = model.generate(**inputs)
    result = processor.decode(out[0], skip_special_tokens=True)
    print(res)
    # # processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
    # # model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
    # img_url = 'https://storage.googleapis.com/sfr-vision-language-research/BLIP/demo.jpg' 
    # raw_image = Image.open(requests.get(img_url, stream=True).raw).convert('RGB')
    # # raw_image = Image.open('puppy.jpg').convert('RGB')
    # inputs = processor(raw_image, return_tensors="pt")
    # out = model.generate(**inputs)
    # res = processor.decode(out[0], skip_special_tokens=True)
    # print(res)
    # # result = []
    # for image_url in img_urls:
    #     thread_list.append(threading.Thread(target=process, args=[image_url]))
    # for thread in thread_list:
    #     thread.start()
    # for thread in thread_list:
    #     thread.join()
    

        # text = process(image_url)
        # result.append(text)
    

    
   
    #https://storage.googleapis.com/sfr-vision-language-research/BLIP/demo.jpg
    
    print(json.dumps({"activation_id": str(activation_id),
                    "image_url_links": img_urls,
                    "result":res
                }))

    return({"activation_id": str(activation_id),
            "image_url_links": img_urls,
            "result":res
            })

if __name__ == "__main__":
    # print("Line 52.....",sys.argv)
    main(params)