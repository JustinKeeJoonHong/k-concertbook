import boto3
import requests
import json
from decimal import Decimal
from boto3.dynamodb.types import TypeDeserializer
import os

# OpenSearch settings from environment
OPENSEARCH_URL = os.environ.get('OPENSEARCH_URL')
OPENSEARCH_USER = os.environ.get('OPENSEARCH_USER')
OPENSEARCH_PASS = os.environ.get('OPENSEARCH_PASS')

# Deserialize DynamoDB types
deserializer = TypeDeserializer()


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj) if obj % 1 else int(obj)
        return super(DecimalEncoder, self).default(obj)


def lambda_handler(event, context):
    # Send INSERT/MODIFY DynamoDB stream records to OpenSearch
    for record in event.get('Records', []):
        eventName = record.get('eventName')
        if eventName in ('INSERT', 'MODIFY'):
            newImage = record['dynamodb']['NewImage']
            item = {k: deserializer.deserialize(v) for k, v in newImage.items()}
            document_id = item.get('event_id')
            if not OPENSEARCH_URL or not document_id:
                continue
            index_name = 'event'
            url = f"{OPENSEARCH_URL}/{index_name}/_doc/{document_id}"
            try:
                requests.put(
                    url,
                    auth=(OPENSEARCH_USER, OPENSEARCH_PASS) if OPENSEARCH_USER and OPENSEARCH_PASS else None,
                    json=json.loads(json.dumps(item, cls=DecimalEncoder)),
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )
            except Exception:
                # Ignore indexing errors to avoid blocking stream processing
                pass

    return {'statusCode': 200, 'body': json.dumps('DynamoDB -> OpenSearch processing complete')}
