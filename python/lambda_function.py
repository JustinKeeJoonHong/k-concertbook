import json
import os
import requests
from decimal import Decimal

# OpenSearch settings from environment
OPENSEARCH_URL = os.environ.get('OPENSEARCH_URL')
OPENSEARCH_USER = os.environ.get('OPENSEARCH_USER')
OPENSEARCH_PASS = os.environ.get('OPENSEARCH_PASS')


def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


def search(event):
    # Search events in OpenSearch using provided JSON body {"keyword": "..."}
    payload = json.loads(event.get('body', '{}'))
    keyword = payload.get('keyword')
    if not keyword or not OPENSEARCH_URL:
        return {'statusCode': 400, 'body': json.dumps({'error': 'keyword and OPENSEARCH_URL are required'})}

    query = {"query": {"match": {"event_name": keyword}}}
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.get(OPENSEARCH_URL, auth=(OPENSEARCH_USER, OPENSEARCH_PASS) if OPENSEARCH_USER and OPENSEARCH_PASS else None, headers=headers, json=query, timeout=10)
    except Exception as e:
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}

    if response.status_code == 200:
        search_results = response.json()
        hits = search_results.get('hits', {}).get('hits', [])
        if hits:
            return {'statusCode': 200, 'body': json.dumps(hits, default=decimal_default)}
        else:
            return {'statusCode': 404, 'body': json.dumps({'message': 'No events found for the given keyword'})}
    else:
        return {'statusCode': response.status_code, 'body': json.dumps({'error': 'Failed to fetch data from OpenSearch', 'details': response.text})}


def lambda_handler(event, context):
    path = event.get('path', '')
    http_method = event.get('httpMethod', '')
    if path == '/default/ticketmaster_event/search' and http_method == 'POST':
        return search(event)
        return {'statusCode': 400, 'body': json.dumps({'error': 'Unsupported method'})}
