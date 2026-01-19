import boto3
import requests

OBJECT_NAME_TO_UPLOAD = 'IU_image.jpg'

s3_client = boto3.client('s3')

# generate the presigned POST data
response = s3_client.generate_presigned_post(
    Bucket = 'ticketmasterimage',
    Key = OBJECT_NAME_TO_UPLOAD,
    ExpiresIn = 3600
)

# generate a presigned URL for PUT
url = s3_client.generate_presigned_url(
    'put_object',
    Params={'Bucket': 'ticketmasterimage', 'Key': 'upload/IU_image.jpg'},
    ExpiresIn=3600
)
