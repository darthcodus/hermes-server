import json
import urllib

import requests

class YahooWeatherHelper(object):
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = "https://query.yahooapis.com/v1/public/yql?"
        #self.coords_to_weather_cache = {} # map from coords to tuple (timestamp_ms, weather_data)
        #self.cache_expiry_in_milliseconds = {}

    def get_forecase(self, coords):
        weather_data = self._get_weather()
        return weather_data['forecast']

    def get_weather(self, coords, include_forecast=False):
        weather_data = self._get_weather(coords)
        if not include_forecast:
            weather_data.pop('forecast', None)
        return weather_data

    def _get_weather(self, coords):
        yql_query = 'select * from weather.forecast where woeid in '
        yql_query += '(SELECT woeid FROM geo.places WHERE text="({},{})") and u="c"'.format(coords.lat, coords.long)

        yql_url = self._generate_yql_url(yql_query)

        response = requests.get(yql_url)
        if response.status_code != requests.codes.ok:
            return None

        data = json.loads(response.text)
        weather_data = data['query']['results']
        return weather_data['channel']

    def _generate_yql_url(self, yql_query):
        return self.base_url + urllib.parse.urlencode({'q':yql_query}) + "&format=json"


