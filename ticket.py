import json
import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal

# Create DynamoDB resource and table handle
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Ticket_table')



# Helper class to convert Decimal values to JSON-serializable types
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            # Convert Decimal to float if fractional, otherwise to int
            return float(obj) if obj % 1 else int(obj)
        return super(DecimalEncoder, self).default(obj)


def create_item(event):
    # Create a ticket item
    ticket_id = event['ticket_id']
    event_id = event['event_id']
    event_name = event['event_name']
    event_date = event['event_date']
    venue_id = event['venue_id']
    venue_seat = event['venue_seat']
    ticket_price = event['ticket_price']
    ticket_status = event['ticket_status']

    table.put_item(
        Item={
            'ticket_id': ticket_id,
            'event_id': event_id,
            'event_name': event_name,
            'event_date': event_date,
            'venue_id': venue_id,
            'venue_seat': venue_seat,
            'ticket_price': ticket_price,
            'ticket_status': ticket_status
        }
    )
    return {'statusCode': 200, 'body': json.dumps('Ticket successfully created')}


def read_item(event):
    # Read ticket by ticket_id
    ticket_id = event['ticket_id']
    response = table.get_item(Key={'ticket_id': ticket_id})
    if 'Item' in response:
        return {'statusCode': 200, 'body': json.dumps(response['Item'], cls=DecimalEncoder)}
    else:
        return {'statusCode': 404, 'body': json.dumps('Ticket not found')}


def update_item(event):
    # Update ticket item
    ticket_id = event['ticket_id']
    update_expression = "SET event_name=:name, event_date=:date, venue_id=:venue, venue_seat=:seat, ticket_price=:price, ticket_status=:tickets"
    expression_values = {
        ':name': event['event_name'],
        ':date': event['event_date'],
        ':venue': event['venue_id'],
        ':seat': event['venue_seat'],
        ':price': event['ticket_price'],
        ':tickets': event['ticket_status']
    }
    response = table.update_item(Key={'ticket_id': ticket_id}, UpdateExpression=update_expression, ExpressionAttributeValues=expression_values, ReturnValues="UPDATED_NEW")
    if 'Attributes' in response:
        return {'statusCode': 200, 'body': json.dumps('Ticket successfully updated', cls=DecimalEncoder)}
    else:
        return {'statusCode': 404, 'body': json.dumps('Ticket not found')}


def delete_item(event):
    # Delete ticket item
    ticket_id = event['ticket_id']
    response = table.delete_item(Key={'ticket_id': ticket_id})
    if response.get('ResponseMetadata', {}).get('HTTPStatusCode') == 200:
        return {'statusCode': 200, 'body': json.dumps('Ticket successfully deleted')}
    else:
        return {'statusCode': 404, 'body': json.dumps('Ticket not found')}


def lambda_handler(event, context):
    # Route by HTTP method
    http_method = event['httpMethod']
    if http_method == 'POST':
        return create_item(json.loads(event['body']))
    elif http_method == 'GET':
        return read_item(event)
    elif http_method == 'PUT':
        return update_item(json.loads(event['body']))
    elif http_method == 'DELETE':
        return delete_item(json.loads(event['body']))
    else:
        return {'statusCode': 400, 'body': json.dumps('Invalid HTTP method')}
