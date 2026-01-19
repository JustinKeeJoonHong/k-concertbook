import json
import boto3
import redis
import time
import uuid
from boto3.dynamodb.conditions import Key
import os

# DynamoDB client
dynamodb = boto3.client('dynamodb')

# Redis connection: host configurable via `REDIS_HOST` environment variable
REDIS_HOST = os.environ.get('REDIS_HOST', 'redis-ticket-if7udi.serverless.usw2.cache.amazonaws.com')
redis_client = redis.StrictRedis(
    host=REDIS_HOST,
    port=int(os.environ.get('REDIS_PORT', 6379)), 
    db=0,
    ssl=bool(os.environ.get('REDIS_SSL', True))
)

def reserve_ticket(event):

    body = json.loads(event['body'])
    ticket_ids = body.get('ticket_ids', [])

    if ticket_ids:
        for ticket_id in ticket_ids:
            redis_client.setex(ticket_id, 300, 'reserved')

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Tickets saved in Redis for 5 minutes'})
        }
    else:
        return {
            'statusCode': 400,
            'body': json.dumps({'error':'No ticket_ids found in request body for reserve ticket'})
        }

def complete_purchase_ticket(event):
    body = json.loads(event['body'])
    ticket_ids = body.get('ticket_ids', [])
    event_id = body.get('event_id')
    
    # ticket_ids printed for debugging removed
    if not ticket_ids:
        return {
            'statusCode' : 400,
            'body' : json.dumps({'error' : 'No ticket_ids found in request'})
        }
    
    booking_id = str(uuid.uuid4())

    created_at = str(int(time.time()))

    update_expression = "SET ticket_status=:status"
    expression_values = {
        ':status': {'S': 'sold'},
        ':current_status': {'S': 'available'}
    }

    transact_items = []

    for ticket_id in ticket_ids:
        transact_items.append({
            'Update': {
                'TableName' : 'Ticket_table',
                'Key' : {
                    'ticket_id': {'S' : ticket_id}
                },
                'UpdateExpression' : update_expression,
                'ConditionExpression': "ticket_status = :current_status",
                'ExpressionAttributeValues' : expression_values
            }
        })
    
    # transact_items debug output removed

    transact_items.append({
                'Put': {
            'TableName' : 'Booking_table',
            'Item' : {
                'booking_id': {'S': booking_id},
                'booking_status': {'S': 'purchase complete'},
                'ticket_ids': {'L': [{'S': ticket_id} for ticket_id in ticket_ids]},  # List of ticket IDs
                'createdAt': {'N': created_at}
            }
        }
    })
    ticket_count = len(ticket_ids)

    transact_items.append({
        'Update': {
            'TableName' : 'Event_table',
            'Key' : {
                'event_id' : {'S' : event_id}
            },
            'UpdateExpression' : "SET available_tickets = available_tickets - :count",
            'ConditionExpression' : "available_tickets >= :count",
            'ExpressionAttributeValues' : {
                        ':count': {'N': str(ticket_count)}
                    }
        }
    })
    # transact_items debug output removed

    try:
        dynamodb.transact_write_items(TransactItems= transact_items)
        return {
            'statusCode' : 200,
            'body' : json.dumps({'message' : 'complete booking tickets', 'booking_id' : booking_id})
        }
    except Exception as e:
        # transaction failure details returned in response
        return {
            'statusCode': 500,
            'body' : json.dumps({'error' : 'Transaction failed', 'details': str(e)})
        }

    



def lambda_handler(event, context):
    
    path = event['path']  
    http_method = event['httpMethod']  

    if path == "/default/ticketmaster_booking/reserve" and http_method == "POST":
        return reserve_ticket(event)
    
    elif path == "/default/ticketmaster_booking/purchase" and http_method == "POST":
        return complete_purchase_ticket(event)
    
    else:
        return {
            'statusCode': 404,
            'body': json.dumps({'error': 'Invalid path or method'})
        }
