import json
import boto3

dynamodb = boto3.resource('dynamodb')
image_table = dynamodb.Table('Image_table')

def add_image_dynamoDB(s3_record):
    bucket_name = s3_record['s3']['bucket']['name']
    object_key = s3_record['s3']['object']['key']
    event_time = s3_record['eventTime']
    image_url = f"https://d3n5cjruhfi9i8.cloudfront.net/{object_key}"
    item = {
        'image_id': object_key,
        'bucket_name': bucket_name,
        'object_key': object_key,
        'image_url' : image_url,
        'event_time': event_time
    }
    image_table.put_item(Item=item)
    

def delete_image_dynamoDB(s3_record):
    image_id = s3_record['s3']['object']['key']
    response = image_table.delete_item(
        Key={
            'image_id': image_id
        }
    )
    



def lambda_handler(event, context):
    # Process SQS messages that contain S3 event notifications

    try:
        for record in event['Records']:
            body = json.loads(record['body'])
            s3_record = body['Records'][0]
            if s3_record['eventName'] == 'ObjectCreated:Put':
                add_image_dynamoDB(s3_record)
            elif s3_record['eventName'] == 'ObjectRemoved:Delete':
                delete_image_dynamoDB(s3_record)            
    except Exception as e:
        raise e        
    # TODO implement
    return {
        'statusCode': 200,
        'body': json.dumps('OK')
    }
