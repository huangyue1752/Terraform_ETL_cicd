import requests
from bs4 import BeautifulSoup
import time
import pandas as pd
import asyncio
from azure.eventhub.aio import EventHubProducerClient
from azure.eventhub import EventData
import json
import nest_asyncio

nest_asyncio.apply()

class WeatherDataIngestion:
    def __init__(self, city, eventhub_conn_str, eventhub_name):
        self.city = city
        self.eventhub_conn_str = eventhub_conn_str
        self.eventhub_name = eventhub_name

    def get_weather_data(self):
        """Fetch weather data for a given city by scraping Google."""
        url = f"https://www.google.com/search?q=weather+{self.city}"
        html = requests.get(url).content
        soup = BeautifulSoup(html, 'html.parser')

        temp = soup.find('div', attrs={'class': 'BNeawe iBp4i AP7Wnd'}).text
        details = soup.find('div', attrs={'class': 'BNeawe tAd8D AP7Wnd'}).text
        data = details.split('\n')
        time_of_day, sky_condition = data[0], data[1]

        
        dataframe = pd.DataFrame([[temp, time_of_day, sky_condition]], 
                                 columns=['temperature', 'time', 'skycondition'])
        return dataframe.to_json(orient='records', lines=True)

    async def send_to_eventhub(self, data):
        """Send the scraped weather data to Azure Event Hubs."""
        producer = EventHubProducerClient.from_connection_string(
            conn_str=self.eventhub_conn_str, eventhub_name=self.eventhub_name)

        async with producer:
            event_data_batch = await producer.create_batch()
            event_data_batch.add(EventData(data))
            await producer.send_batch(event_data_batch)
            print("Data sent successfully to Event Hubs.")

    async def stream_weather_data(self, interval=30):
        """Stream weather data at regular intervals."""
        while True:
            try:
                data = self.get_weather_data()
                data_json = json.loads(data)
                await self.send_to_eventhub(json.dumps(data_json))
                time.sleep(interval)  # Sleep between data collections
            except Exception as e:
                print(f"Error: {e}")
            await asyncio.sleep(interval)
            print(data_json)

# Example function to run the streaming framework
async def run_weather_stream(city, conn_str, eventhub_name, interval=30):
    ingestion = WeatherDataIngestion(city, conn_str, eventhub_name)
    await ingestion.stream_weather_data(interval)

if __name__ == "__main__":
    city = "New York"
    conn_str = 'Endpoint=sb://streamingdata-demo-dev.servicebus.windows.net/;SharedAccessKeyName=weatherdata-policy;SharedAccessKey=y8tGytHlo6RMIIIyWSzJRONpl5wvr42Xn+AEhDyJg34=;EntityPath=weatherdata-streaming-demo-dev'
    eventhub_name = 'weatherdata-streaming-demo-dev'

    loop = asyncio.get_event_loop()
    try:
        asyncio.ensure_future(run_weather_stream(city, conn_str, eventhub_name, interval=30))
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
