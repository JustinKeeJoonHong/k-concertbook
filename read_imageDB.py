import json
import json
import boto3
from botocore.exceptions import ClientError
import json
import boto3
from botocore.exceptions import ClientError

# DynamoDB and S3 clients
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Image_table')


def lambda_handler(event, context):
    # Return JSON list of image URLs stored in DynamoDB
    try:
        response = table.scan()
        items = response.get('Items', [])
        image_urls = [item.get('image_url') for item in items if item.get('image_url')]
        return {
            'statusCode': 200,
            'body': json.dumps({'image_urls': image_urls})
        }
    except ClientError as e:
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}
    except Exception as e:
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}
