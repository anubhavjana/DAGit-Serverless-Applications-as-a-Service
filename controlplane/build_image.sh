#!/bin/bash

#  ./register.sh /decode-function /decode decode-action [SAMPLE USE]

function_dir_name=$1
docker_image_name=$2

cd $function_dir_name

chmod -R 777 ./

./buildAndPush.sh $docker_image_name
