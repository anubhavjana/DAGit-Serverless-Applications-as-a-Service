# # Dockerfile for Python whisk docker action
# FROM openwhisk/dockerskeleton

# ENV FLASK_PROXY_PORT 8080

# ## Install our action's Python dependencies
# ADD requirements.txt /action/requirements.txt
# RUN apk --update add python py-pip openssl ca-certificates py-openssl wget git
# RUN apk --update add --virtual build-dependencies libffi-dev openssl-dev python-dev py-pip build-base && apk add jpeg-dev zlib-dev libjpeg && pip install --upgrade pip
# RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
# ENV PATH="/root/.cargo/bin:${PATH}"
# # RUN pip install tokenizers
# # RUN apk --update add world build-essential
# RUN cd /action; pip install -r requirements.txt
# # RUN pip install torch===1.4.0 torchvision===0.5.0 -f https://download.pytorch.org/whl/torch_stable.html
# # RUN pip install torch===1.4.0 -f https://download.pytorch.org/whl/torch_stable.html
# ENV USE_OPENMP=0
# ENV OMP_NUM_THREADS=1
# RUN apk --update add gcompat libc6-compat musl musl-dev
# RUN apk add --no-cache libgcc ncurses-libs libstdc++
# # ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/lib/python3.6/site-packages/torch/lib/:/usr/local/lib/python3.6/site-packages/torch/lib//

# RUN pip install torch==1.10.2+cpu -f https://download.pytorch.org/whl/torch_stable.html
# # ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/lib/ld-linux-x86-64.so.2:/usr/local/lib/python3.6/site-packages/torch/lib/
# # ENV LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libgomp.so.1://usr/local/lib/python3.6/site-packages/torch/lib//libgomp-a34b3233.so.1
# # ENV LD_LIBRARY_PATH=/usr/local/lib/python3.6/site-packages/torch/lib/:/usr/local/lib/python3.6/site-packages/torch/lib//libgomp-a34b3233.so.1
# # ENV LD_LIBRARY_PATH=/usr/local/lib/python3.6/site-packages/torch/lib:$LD_LIBRARY_PATH

# # RUN pip install torch===2.0.0 torchvision===0.15.1


# # Ensure source assets are not drawn from the cache after this date
# ENV REFRESHED_AT 2016-09-05T13:59:39Z
# # Add all source assets
# ADD . /action
# # Rename our executable Python action
# ADD img_text.py /action/exec

# # Leave CMD as is for Openwhisk
# CMD ["/bin/bash", "-c", "cd actionProxy && python3 -u actionproxy.py"]


FROM ibmfunctions/action-python-v3.9

#download pip packages

RUN pip install --upgrade pip

RUN pip install transformers requests redis pilgram Pillow==6.2.2 zlib-state torch

ADD img_text.py /action/exec

# RUN python3 -c "from huggingface_hub import snapshot_download,hf_hub_download;REPO_ID = 'Salesforce/blip-image-captioning-base';snapshot_download(repo_id='Salesforce/blip-image-captioning-base',local_dir='/action/models/transformers')"

ADD models /action/models

CMD ["/bin/bash", "-c", "cd actionProxy && python3 -u actionproxy.py"]

#download pre-trained model from hugging face to docker image
# RUN pip install sentence_transformers
# RUN python3 -c "from transformers import BlipProcessor, BlipForConditionalGeneration;model = BlipForConditionalGeneration.from_pretrained('Salesforce/blip-image-captioning-base');model.save('models')"
# COPY models .


# ADD img_text.py .

# CMD ["python3","img_text.py"]


# RUN ls /action/1/bin/models/transformers
# CMD ['echo','/action/1/bin/models/transformers']
# CMD ['cat','/action/1/bin/models/transformers/exec']
# CMD ['ls','/action/1/bin/models/transformers']

# FROM python:3.9-slim-buster

# RUN apt-get update

# #download pip packages

# RUN pip install --upgrade pip

# RUN pip install transformers

# RUN pip install requests

# RUN pip install redis

# RUN pip install pilgram

# # RUN apt-get install jpeg-dev zlib-dev

# RUN pip install Pillow

# RUN pip install zlib-state

# RUN pip install torch

# RUN python3 -c "from huggingface_hub import snapshot_download,hf_hub_download;REPO_ID = 'Salesforce/blip-image-captioning-base';snapshot_download(repo_id='Salesforce/blip-image-captioning-base',local_dir='/models/transformers')"

# RUN ls /


# FROM openwhisk/python3action
# RUN apk update 
# # RUN apk add build-dependencies libffi-dev openssl-dev python-dev py-pip build-base
# RUN pip3 install --upgrade pip
# RUN pip3 install transformers redis requests boto3 Pillow torch pilgram
# RUN python3 -c "from huggingface_hub import snapshot_download,hf_hub_download;REPO_ID = 'Salesforce/blip-image-captioning-base';snapshot_download(repo_id='Salesforce/blip-image-captioning-base',local_dir='/models/transformers')"
# RUN ls /

