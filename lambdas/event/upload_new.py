import boto3
import requests
import json
from decimal import Decimal
from boto3.dynamodb.types import TypeDeserializer
import os

# OpenSearch configuration via environment
OPENSEARCH_URL = os.environ.get('OPENSEARCH_URL', 'https://search-ticketmasterdomain-o6opkdsmctza4ui7frhdsg6e2q.us-west-2.es.amazonaws.com')
OPENSEARCH_USER = os.environ.get('OPENSEARCH_USER')
OPENSEARCH_PASS = os.environ.get('OPENSEARCH_PASS')

# TypeDeserializer initialization
deserializer = TypeDeserializer()

# Custom JSON encoder for Decimal
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            if obj % 1 > 0:
                return float(obj)
            else:
                return int(obj)
        return super(DecimalEncoder, self).default(obj)

# Lambda handler
def lambda_handler(event, context):
    for record in event['Records']:
        eventName = record['eventName']
        if eventName == 'INSERT' or eventName == 'MODIFY':
            newImage = record['dynamodb']['NewImage']
            item = {k: deserializer.deserialize(v) for k, v in newImage.items()}
            document_id = item['event_id']
            index_name = "event"
            url = f"{OPENSEARCH_URL}/{index_name}/_doc/{document_id}"
            response = requests.put(
                url, 
                auth=(OPENSEARCH_USER, OPENSEARCH_PASS) if OPENSEARCH_USER and OPENSEARCH_PASS else None, 
                json=json.dumps(item, cls=DecimalEncoder), 
                headers={'Content-Type': 'application/json'}
            )
    return {
        'statusCode': 200,
        'body': json.dumps('DynamoDB data successfully sent to OpenSearch')
    }
