import json
import boto3

s3 = boto3.client('s3')

def lambda_handler(event, context):
    filename = event['queryStringParameters']['filename']
    # generate a presigned URL for uploading an image
    url = s3.generate_presigned_url(
        'put_object',
        Params={
            'Bucket': 'ticketmasterimage',
            'Key': filename,
            'ContentType': 'image/jpeg'
        },
        ExpiresIn=3600
    )
    return {
        'statusCode': 200,
        'body': json.dumps({'url':url, 'filename': filename})
    }
