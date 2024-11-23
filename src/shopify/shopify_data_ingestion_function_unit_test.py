import unittest
from unittest.mock import patch, AsyncMock
import json
from shopify.shopify_data_ingestion_library import IngestionFramework  # Replace with the actual module name


class TestIngestionFramework(unittest.TestCase):
    
    @patch('shopify_ingestion_library.EventHubProducerClient')
    @patch('shopify_ingestion_library.pubsub_v1.SubscriberClient')
    def test_process_message(self, mock_subscriber_client, mock_eventhub_client):
        # Arrange
        ingestion_framework = IngestionFramework('subscription_name', 'conn_str', 'eventhub_name')

        # Mock message data
        message_data = {
            'id': '123',
            'cancel_reason': 'none',
            'cancelled_at': None,
            'checkout_id': 'checkout_1',
            'created_at': '2024-01-01T00:00:00Z',
            'customer_locale': 'en_US',
            'financial_status': 'pad',
            'presentment_currency': 'USD',
            'processed_at': '2024-01-01T01:00:00Z',
            'subtotal_price': '100.00',
            'billing_address': {'street': '123 Main St'},
            'line_items': [{'item': 'item1', 'price': '50.00'}, {'item': 'item2', 'price': '50.00'}]
        }

        mock_message = AsyncMock()
        mock_message.data = json.dumps(message_data).encode('utf-8')

        # Mock the EventHubProducerClient and its methods
        mock_eventhub_producer = AsyncMock()
        mock_eventhub_client.from_connection_string.return_value.__aenter__.return_value = mock_eventhub_producer
        mock_eventhub_producer.create_batch.return_value = AsyncMock()
        mock_eventhub_producer.send_batch.return_value = AsyncMock()

        # Act
        ingestion_framework.process_message(mock_message)

        # Assert
        mock_eventhub_producer.create_batch.assert_called_once()
        mock_eventhub_producer.send_batch.assert_called_once()
        mock_message.ack.assert_called_once()

    @patch('shopify_ingestion_library.pubsub_v1.SubscriberClient')
    def test_start(self, mock_subscriber_client):
        # Arrange
        subscription_name = 'test-subscription'
        event_hub_conn_str = 'test-connection-string'
        event_hub_name = 'test-event-hub'

        ingestion_framework = IngestionFramework(subscription_name, event_hub_conn_str, event_hub_name)

        # Mock the subscriber
        mock_future = AsyncMock()
        mock_subscriber_client.return_value.subscribe.return_value = mock_future

        # Act
        ingestion_framework.start()

        # Assert
        mock_subscriber_client.assert_called_once()
        mock_subscriber_client.return_value.subscribe.assert_called_once_with(subscription_name, callback=ingestion_framework.process_message) 


if __name__ == '__main__':
    unittest.main()
