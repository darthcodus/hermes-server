import time

from utils.elastic_search_handler import *
from utils.uber_helper import *
from utils.yahoo_weather_helper import *
from utils.coords import *

logger = logging.getLogger(__name__)

#class ExpiringCacheApiHelper(object):

def _get_uber_product_details_list(start_coords, end_coords, uber_helper):
    time_estimates = uber_helper.get_pickup_time_estimates(start_coords)

    price_estimates = uber_helper.get_price_estimates(start_coords, end_coords)['prices']
    product_id_to_price_estimate_map = {price_estimate['product_id']: price_estimate for price_estimate in price_estimates}

    product_id_to_product_map = {}
    for time_estimate in time_estimates['times']:
        product_id = time_estimate['product_id']
        price_estimate = product_id_to_price_estimate_map[product_id]

        product_details = { key: val for key, val in time_estimate.items()}
        product_details.update(price_estimate)

        product_id_to_product_map[time_estimate['product_id']] = UberProduct(**product_details)

        product = product_id_to_product_map[product_id]
        logger.debug('Found: id: {}, name: {}'.format(product.product_id, product.display_name))

        # needs request scope, skipping for now
        # price_estimate = uber_helper.get_price_estimate_for_product(apt_coords, symc_coords, product.id)
    return product_id_to_product_map

def _generate_context_data(weather_data, start_coords, end_coords):
    context_data = {}
    context_data['weather'] = weather_data
    context_data['start_latitude'] = start_coords.lat
    context_data['start_longitude'] = start_coords.long
    context_data['end_latitude'] = end_coords.lat
    context_data['end_longitude'] = end_coords.long
    return  context_data


def main():
    apt_coords = Coords(34.024314, -118.297941)
    symc_coords = Coords(33.988031, -118.388916)

    with open("config.json") as f:
        config = json.load(f, encoding='utf-8')

    uber_access_token = config["uber_api"]["debug_access_token"]
    uber_server_token = config["uber_api"]["server_token"]
    uber_client_id = config["uber_api"]["client_id"]
    uber_client_secret = config["uber_api"]["client_secret"]

    try:
        timestamp = int(time.time())

        yahoo_client_id = config["yahoo_weather_api"]["client_id"]
        yahoo_client_secret = config["yahoo_weather_api"]["client_secret"]
        weather_data = YahooWeatherHelper(yahoo_client_id, yahoo_client_secret).get_weather(apt_coords)

        uber_helper = UberHelper(uber_server_token, OAuth2Credential(access_token=uber_access_token,
                                                                     client_id=uber_client_id,
                                                                     client_secret=uber_client_secret,
                                                                     expires_in_seconds=999999,
                                                                     scopes={'ride_widgets', 'request'},
                                                                     grant_type=''
                                                                     ))
        uber_details_list = _get_uber_product_details_list(apt_coords, symc_coords, uber_helper)

        context_data = _generate_context_data(weather_data, apt_coords, symc_coords)

        print(context_data)
        es_connection = ElasticSearchConnection(hosts=['http://127.0.0.1:9200/'])
        IndicesHandler(es_connection).create_index_if_not_exist('uber_prices')
        ElasticSearchHandler(es_connection).push_group(parent_data={'timestamp': timestamp, 'context': context_data},
                                                       parent_doc_type='time_instant_for_coords',
                                                       es_obj_list=uber_details_list,
                                                       doc_type=uber_details_list[0].doc_type()
                                                       )
    except Exception as e:
        logger.error("An exception occurred: {}".format(e))
        raise

main()
