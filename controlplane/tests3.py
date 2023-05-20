import os
import boto3
from botocore.exceptions import ClientError

aws_access_key_id = os.environ.get('AWS_ACCESS_KEY_ID')
aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
aws_region = os.getenv('AWS_REGION')
print(aws_access_key_id,aws_secret_access_key)

# s3 = boto3.client('s3', aws_access_key_id=aws_access_key_id,aws_secret_access_key=aws_secret_access_key,region_name=aws_region)

# upload_file_path = "dag_register.py"
# bucket_name = 'dagit-store'
# key_name = upload_file_path
# folder_path = 'images'
# folder_name = "images"
# try:
#     s3.upload_file(upload_file_path,bucket_name,key_name)
#     s3.put_object_acl(Bucket=bucket_name, Key=key_name, ACL='public-read')
#     object_url = "https://dagit-store.s3.ap-south-1.amazonaws.com/"+key_name
#     print("Uploaded....\n")
#     print(object_url)
# except ClientError as e:
#     print(e)
# loop through files in folder
# for subdir, dirs, files in os.walk(folder_path):
#     for file in files:
#         # get full path of file
#         file_path = os.path.join(subdir, file)
#         # get S3 object key
#         object_key = os.path.relpath(file_path, folder_path)
#         # upload file to S3
#         # s3.Object(bucket_name, object_key).upload_file(file_path)
#         # s3.upload_file(file_path,bucket_name,object_key)
#         s3.upload_file(file_path, bucket_name, f'{folder_name}/{file_path.split("/")[-1]}')
#         s3.put_object_acl(Bucket=bucket_name, Key=f'{folder_name}/{file_path.split("/")[-1]}', ACL='public-read')
# print("Uploaded....\n")





# try:

#     response = s3.generate_presigned_url('get_object',
#                                          Params={'Bucket': bucket_name,
#                                                  'Key': key_name},
#                                          ExpiresIn=3600)
#     print(response)
# except ClientError as e:
#     print(e)