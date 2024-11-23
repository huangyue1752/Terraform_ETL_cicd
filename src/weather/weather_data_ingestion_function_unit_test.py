
import json
from weather_data_ingestion_function import WeatherDataIngestion  # Replace with actual module name
from unittest.mock import patch, AsyncMock
import unittest
import asyncio
import nest_asyncio

nest_asyncio.apply()

class TestWeatherDataIngestion(unittest.TestCase):
    # Your test methods here...
    def setUp(self):
        """Set up the test case with initial parameters."""
        self.city = "New York"
        self.eventhub_conn_str = 'your_eventhub_connection_string'
        self.eventhub_name = 'your_eventhub_name'
        self.weather_ingestion = WeatherDataIngestion(self.city, self.eventhub_conn_str, self.eventhub_name)

    @patch('requests.get')
    @patch('azure.eventhub.aio.EventHubProducerClient')
    async def test_get_weather_data(self, mock_eventhub_client, mock_requests_get):
        """Test the get_weather_data method."""
        # Simulate the HTML content returned by the requests.get call
        mock_html_content = """
            <div class='BNeawe iBp4i AP7Wnd'>75°F</div>
            <div class='BNeawe tAd8D AP7Wnd'>Afternoon\nClear</div>
        """
        mock_requests_get.return_value.content = mock_html_content.encode('utf-8')

        # Call the method under test
        data_json = self.weather_ingestion.get_weather_data()

        # Assert the expected output
        expected_output = json.dumps([{
            'temperature': '75°F',
            'time': 'Afternoon',
            'sky_condition': 'Clear'
        }], orient='records')

        self.assertEqual(data_json, expected_output)

    @patch('requests.get')
    @patch('azure.eventhub.aio.EventHubProducerClient')
    @patch('asyncio.sleep', new_callable=AsyncMock)  # Mock sleep to avoid delays
    async def test_send_to_eventhub(self, mock_async_sleep, mock_eventhub_client, mock_requests_get):
        """Test the send_to_eventhub method."""
        # Simulate the HTML content returned
        mock_html_content = """
            <div class='BNeawe iBp4i AP7Wnd'>75°F</div>
            <div class='BNeawe tAd8D AP7Wnd'>Afternoon\nClear</div>
        """
        mock_requests_get.return_value.content = mock_html_content.encode('utf-8')

        # Mock EventHubProducerClient behavior
        mock_producer = AsyncMock()
        mock_eventhub_client.from_connection_string.return_value = mock_producer

        # Call the method under test
        weather_data = self.weather_ingestion.get_weather_data()
        await self.weather_ingestion.send_to_eventhub(weather_data)

        # Assert that the send_batch method was called
        mock_producer.create_batch.assert_awaited_once()
        self.assertTrue(mock_producer.send_batch.called)

    @patch('asyncio.sleep', new_callable=AsyncMock)  # Mock sleep to avoid delays
    @patch('requests.get')
    @patch('azure.eventhub.aio.EventHubProducerClient')
    async def test_stream_weather_data(self, mock_eventhub_client, mock_requests_get, mock_async_sleep):
        """Test the stream_weather_data method."""
        # Mock the responses for weather data
        mock_html_content = """
            <div class='BNeawe iBp4i AP7Wnd'>75°F</div>
            <div class='BNeawe tAd8D AP7Wnd'>Afternoon\nClear</div>
        """
        mock_requests_get.return_value.content = mock_html_content.encode('utf-8')

        # Mock EventHubProducerClient behavior
        mock_producer = AsyncMock()
        mock_eventhub_client.from_connection_string.return_value = mock_producer

        # Run the stream method (we'll limit it to a single iteration for the test)
        task = asyncio.create_task(self.weather_ingestion.stream_weather_data(interval=1))
        await asyncio.sleep(1.5)  # Allow some time for the loop to run once
        task.cancel()  # Stop the loop after testing

        # Assert that the correct methods were called
        self.assertTrue(mock_producer.create_batch.called)
        self.assertTrue(mock_producer.send_batch.called)
# Run the tests
suite = unittest.TestLoader().loadTestsFromTestCase(TestWeatherDataIngestion)
unittest.TextTestRunner(verbosity=2).run(suite)
