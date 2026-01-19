import json
import boto3
import string
import redis
import requests
from boto3.dynamodb.conditions import Key
from decimal import Decimal
import os

# Create DynamoDB resource and table handles
dynamodb = boto3.resource('dynamodb')
event_table = dynamodb.Table('Event_table')
ticket_table = dynamodb.Table('Ticket_table')
venue_table = dynamodb.Table('Venue_table')

redis_client = redis.StrictRedis(
    host=os.environ.get('REDIS_HOST', 'redis-ticket-if7udi.serverless.usw2.cache.amazonaws.com'),
    port=int(os.environ.get('REDIS_PORT', 6379)), 
    db=0,
    ssl=bool(os.environ.get('REDIS_SSL', True))
)

# OpenSearch configuration via environment variables
OPENSEARCH_URL = os.environ.get('OPENSEARCH_URL', 'https://search-ticketmasterdomain-o6opkdsmctza4ui7frhdsg6e2q.us-west-2.es.amazonaws.com/event/_search')
OPENSEARCH_USER = os.environ.get('OPENSEARCH_USER')
OPENSEARCH_PASS = os.environ.get('OPENSEARCH_PASS')

alphabet = string.ascii_uppercase

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def validate_event_data(event):
    required_fields = ['event_id', 'event_name', 'event_date', 'venue_id', 'ticket_price']
    for field in required_fields:
        if field not in event:
            return False, f"Missing required field: {field}"
    return True, ""

def generate_seat_map(row_count, seats_per_row):
    seat_map = []
    for row_num in range(row_count):
        row = alphabet[row_num]
        for seat_num in range(1, seats_per_row + 1):
            seat_map.append(f"{row}{seat_num}")
    return seat_map

def get_venue_seat_info(venue_id):
    response = venue_table.get_item(Key={'venue_id': venue_id})
    if 'Item' in response:
        if 'row_count' not in response['Item'] or 'seats_per_row' not in response['Item']:
            raise ValueError("Seat info missing: row_count or seats_per_row is missing in the venue data.")
        row_count = int(response['Item']['row_count'])
        seats_per_row = int(response['Item']['seats_per_row'])
        return row_count, seats_per_row
    else:
        raise ValueError("Venue not found.")

def create_tickets_for_event(event_id, seat_map, ticket_price, venue_id, event_date):
    for seat in seat_map:
        ticket_id = f"{event_id}_{seat}"
        ticket_table.put_item(
            Item={
                'ticket_id': ticket_id,
                'event_id': event_id,
                'seat_number': seat,
                'ticket_price': ticket_price,
                'venue_id': venue_id,
                'event_date': event_date,
                'ticket_status': "available",
                'redis_status' : 'non-exist'
            }
        )
    return {'statusCode': 200, 'body': json.dumps({'message': 'Tickets successfully created'})}

def create_item(event):
    is_valid, message = validate_event_data(event)
    if not is_valid:
        return {'statusCode': 400, 'body': json.dumps({'error': message})}

    event_id = event['event_id']
    event_name = event['event_name']
    event_date = event['event_date']
    venue_id = event['venue_id']
    ticket_price = event['ticket_price']

    row_count, seats_per_row = get_venue_seat_info(venue_id)
    if row_count is None or seats_per_row is None:
        return {'statusCode': 404, 'body': json.dumps({'error': 'Venue not found or seat info missing'})}

    event_table.put_item(
        Item={
            'event_id': event_id,
            'event_name': event_name,
            'event_date': event_date,
            'venue_id': venue_id,
            'ticket_price': ticket_price,
            'available_tickets': row_count * seats_per_row
        }
    )

    seat_map = generate_seat_map(row_count, seats_per_row)
    ticket_creation_response = create_tickets_for_event(event_id, seat_map, ticket_price, venue_id, event_date)
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Event and Tickets successfully created',
            'event_id': event_id,
            'tickets_status': json.loads(ticket_creation_response['body'])['message']
        })
    }

def read_item(event):
    event_id = event['queryStringParameters']['event_id']
    ticket_response = ticket_table.query(
        IndexName='event_id-ticket_status-index',
        KeyConditionExpression=Key('event_id').eq(event_id) & Key('ticket_status').eq('available')
    )
    available_tickets = ticket_response.get('Items', [])
    tickets_not_in_redis = [t for t in available_tickets if not redis_client.exists(t['ticket_id'])]
    if not tickets_not_in_redis:
        return {'statusCode' : 404, 'body': json.dumps({'message': 'No available tickets found'})}
    return {'statusCode': 200, 'body': json.dumps({'available_tickets': tickets_not_in_redis}, default=decimal_default)}

def update_item(event):
    event = json.loads(event['body'])
    event_id = event['event_id']
    venue_id = event['venue_id']
    row_count, seats_per_row = get_venue_seat_info(venue_id)
    update_expression = "SET event_name=:name, event_date=:date, venue_id=:venue, ticket_price=:price, available_tickets=:tickets"
    expression_values = {
        ':name': event['event_name'],
        ':date': event['event_date'],
        ':venue': event['venue_id'],
        ':price': event['ticket_price'],
        ':tickets': row_count * seats_per_row
    }
    response = event_table.update_item(Key={'event_id': event_id}, UpdateExpression=update_expression, ExpressionAttributeValues=expression_values, ReturnValues="UPDATED_NEW")
    if 'Attributes' in response:
        return {'statusCode': 200, 'body': json.dumps({'message': 'Item successfully updated'})}
    else:
        return {'statusCode': 404, 'body': json.dumps({'error': 'Item not found'})}

def delete_item(event):
    event = json.loads(event['body'])
    event_id = event['event_id']
    response = event_table.delete_item(Key={'event_id': event_id})
    if response.get('ResponseMetadata', {}).get('HTTPStatusCode') == 200:
        return {'statusCode': 200, 'body': json.dumps({'message': 'Item successfully deleted'})}
    else:
        return {'statusCode': 404, 'body': json.dumps({'error': 'Item not found'})}

def search(event):
    event = json.loads(event['body'])
    keyword = event['keyword']
    query = {"query": {"match": {"event_name": keyword}}}
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.get(OPENSEARCH_URL, auth=(OPENSEARCH_USER, OPENSEARCH_PASS) if OPENSEARCH_USER and OPENSEARCH_PASS else None, headers=headers, data=json.dumps(query), timeout=10)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        return {'statusCode': 504, 'body': json.dumps({'error': 'OpenSearch request timed out'})}
    except requests.exceptions.ConnectionError as e:
        return {'statusCode': 502, 'body': json.dumps({'error': 'Connection error', 'details': str(e)})}
    except requests.exceptions.HTTPError as e:
        return {'statusCode': e.response.status_code, 'body': json.dumps({'error': 'OpenSearch HTTP error', 'details': e.response.text})}
    except requests.exceptions.RequestException as e:
        return {'statusCode': 500, 'body': json.dumps({'error': 'Request failed', 'details': str(e)})}
    if response.status_code == 200:
        search_results = response.json()
        if search_results.get('hits', {}).get('total', {}).get('value', 0) > 0:
            return {'statusCode': 200, 'body': json.dumps(search_results['hits']['hits'], default=decimal_default)}
        else:
            return {'statusCode': 404, 'body': json.dumps({'message': 'No events found for the given keyword'})}
    else:
        return {'statusCode': response.status_code, 'body': json.dumps({'error': 'Failed to fetch data from OpenSearch', 'details': response.text})}

def lambda_handler(event, context):
    http_method = event['httpMethod']
    path = event['path']
    if path == "/default/ticketmaster_event/search" and http_method =='POST':
        return search(event)
    elif http_method == 'POST':
        return create_item(json.loads(event['body']))
    elif http_method == 'GET':
        return read_item(event)
    elif http_method == 'PUT':
        return update_item(event)
    elif http_method == 'DELETE':
        return delete_item(event)
    else:
        return {'statusCode': 400, 'body': json.dumps({'error': 'Unsupported method'})}
