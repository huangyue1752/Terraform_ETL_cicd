#import os
import json
#import time as t
import asyncio
from google.cloud import pubsub_v1
from azure.eventhub.aio import EventHubProducerClient
from azure.eventhub import EventData


class IngestionFramework:
    def __init__(self, subscription_name, event_hub_conn_str, event_hub_name):
        self.subscription_name = subscription_name
        self.event_hub_conn_str = event_hub_conn_str
        self.event_hub_name = event_hub_name

    async def send_to_event_hub(self, order_data):
        """Send the order data to Azure Event Hub."""
        async with EventHubProducerClient.from_connection_string(
            conn_str=self.event_hub_conn_str, 
            eventhub_name=self.event_hub_name) as producer:
            
            # Create a batch and add events
            event_data_batch = await producer.create_batch()
            event_data_batch.add(EventData(json.dumps(order_data)))
            
            # Send the batch of events to the event hub
            await producer.send_batch(event_data_batch)
            print(order_data)
            print('Data sent successfully to Event Hubs!')

    def process_message(self, message):
        """Process incoming Pub/Sub message."""
        order_data = json.loads(message.data)
        keep = [
            'id', 'cancel_reason', 'cancelled_at', 'checkout_id', 
            'created_at', 'customer_locale', 'financial_status', 
            'presentment_currency', 'processed_at', 'subtotal_price', 
            'billing_address', 'line_items'
        ]
        
        # Filter the order data
        filtered_order_data = {key: order_data[key] for key in keep}
        
        # Send data to Event Hub asynchronously
        asyncio.run(self.send_to_event_hub(filtered_order_data))
        
        # Acknowledge the message
        message.ack()

    def start(self):
        """Start the Pub/Sub subscriber to listen for messages."""
        subscriber = pubsub_v1.SubscriberClient()
        future = subscriber.subscribe(self.subscription_name, callback=self.process_message)

        with subscriber:
            print(f"Listening for messages on {self.subscription_name}...")
            future.result()  # Block until the subscription is cancelled


# Example usage
if __name__ == "__main__":
    # Set environment variable for Google Cloud credentials
  
    
    # Define configuration
    subscription_name = 'projects/wired-victor-432822-p3/subscriptions/demo1-sub'
    event_hub_conn_str = 'Endpoint=sb://streamingeventhubnamespace.servicebus.windows.net/;SharedAccessKeyName=streamingpolicy;SharedAccessKey=jLsmEQBqzbN4G6wB/96sk/NoppvB5DoTp+AEhCUatbQ=;EntityPath=streamingeventhubs'
    event_hub_name = 'streamingeventhubs'

    # Create and start the ingestion framework
    data_streamer = IngestionFramework(subscription_name, event_hub_conn_str, event_hub_name)
    data_streamer.start()