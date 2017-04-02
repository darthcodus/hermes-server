import json
import logging
import requests
import urllib

from .elastic_search_handler import ElasticSearchDoc
from uber_rides.client import UberRidesClient
from uber_rides.session import Session, OAuth2Credential

logger = logging.getLogger(__name__)


class UberProduct(ElasticSearchDoc):
    DOC_TYPE = 'UberProduct'

    def __init__(self, **kwargs):
        required_keys = ('product_id',)
        self.uber_attrs = kwargs
        kwargs['avg_estimate'] = (kwargs['low_estimate'] + kwargs['high_estimate'])/2
        assert all(key in kwargs for key in required_keys)
        for key, val in kwargs.items():
            setattr(self, key, val)
        # TOOD: convert to USD if not in USD

    def elastic_search_representation(self):
        return self.uber_attrs

    def doc_type(self):
        return UberProduct.DOC_TYPE


class UberHelper(object):
    def __init__(self, server_token=None, oauth2credential=None):
        assert server_token is not None or oauth2credential is not None

        self.server_token = server_token
        self.oauth2credential = oauth2credential

        if server_token:
            self._server_client = UberRidesClient(session=Session(server_token=self.server_token))
        if oauth2credential:
            self._user_client = UberRidesClient(session=Session(oauth2credential=oauth2credential))

    def get_products(self, coords):
        logger.debug("Fetching products")
        response = self._client(False).get_products(latitude=coords.lat, longitude=coords.long)
        return self._validate_response_and_get_json(response)

    def get_pickup_time_estimates(self, start_coords, product_id=None):
        logger.debug("Fetching pickup time estimates")
        response = self._client(False).get_pickup_time_estimates(
            start_latitude=start_coords.lat,
            start_longitude=start_coords.long,
            product_id=product_id
        )
        return self._validate_response_and_get_json(response)

    def get_price_estimate_for_product(self, start_coords, end_coords, product_id, seat_count=1):
        """ Gets upfront fares if available.

        Args:
            start_coords:
            end_coords:
            product_id:
            seats:

        Returns:
        """
        logger.debug("Fetching price estimates")
        response = self._client(True).estimate_ride(
            product_id=product_id,
            start_latitude=start_coords.lat,
            start_longitude=start_coords.long,
            end_latitude=end_coords.lat,
            end_longitude=end_coords.long,
            seat_count=seat_count
        )
        logger.debug("Complete response: {}".format(response))
        return self._validate_response_and_get_json(response)


    def get_price_estimates(self, start_coords, end_coords, seat_count=1):
        """ Get a map from product to the (min, max) rates for that product.
        """
        response = self._client(False).get_price_estimates(
            start_latitude=start_coords.lat,
            start_longitude=start_coords.long,
            end_latitude=end_coords.lat,
            end_longitude=end_coords.long,
            seat_count=seat_count
        )
        return self._validate_response_and_get_json(response)

    @staticmethod
    def _validate_response_and_get_json(response):
        logger.debug("Validating response. Complete response: {}".format(response.__dict__))
        if response.status_code != requests.codes.ok:
            logger.error("An error occurred")
            logger.error("Status code: {}".format(response.status_code))
            return None
        logger.debug("Validated. Returning response json: {}".format(response.json))
        return response.json

    def request_ride(self, start_coords, end_coords):
        raise NotImplementedError()

    def _client(self, needs_oauth_token=False):
        if needs_oauth_token and not self._user_client:
            raise RuntimeError("Needs OAuth token but no oauth2 credentials available")
        if self._user_client:
            return self._user_client
        if self._server_client:
            return self._server_client
