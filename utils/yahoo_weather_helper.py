import json
import logging
import urllib

import requests


logger = logging.getLogger(__name__)


class YahooWeatherHelper(object):
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = "https://query.yahooapis.com/v1/public/yql?"
        #self.coords_to_weather_cache = {} # map from coords to tuple (timestamp_ms, weather_data)
        #self.cache_expiry_in_milliseconds = {}

    def get_forecast(self, coords):
        weather_data = self._get_weather(coords, include_forecase=True)
        if weather_data is None or 'forecast' not in weather_data:
            return None
        return weather_data['forecast']

    def get_weather(self, coords, include_forecast=False):
        weather_data = self._get_weather(coords)
        if weather_data is None:
            return None

        if not include_forecast and 'forecast' in weather_data:
            weather_data.pop('forecast', None)
        return weather_data

    def _get_weather(self, coords):
        logger.debug('Received coords: {}, {}'.format(coords.lat, coords.long))

        yql_query = 'select * from weather.forecast where woeid in '
        yql_query += '(SELECT woeid FROM geo.places WHERE text="({},{})") and u="c"'.format(coords.lat, coords.long)

        yql_url = self._generate_yql_url(yql_query)

        response = requests.get(yql_url)
        logger.debug('Response: {}'.format(response))
        logger.debug('Response text: {}'.format(response.text))
        if response.status_code != requests.codes.ok:
            return None

        try:
            data = json.loads(response.text)
            weather_data = data['query']['results']
            return weather_data['channel']
        except Exception as e:
            logger.error(e)
            return None

    def _generate_yql_url(self, yql_query):
        yql_url = self.base_url + urllib.parse.urlencode({'q':yql_query}) + "&format=json"
        logging.debug("YQL URL: {}".format(yql_url))
        return yql_url
