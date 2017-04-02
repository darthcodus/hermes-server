import datetime
import time

import utils
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
    return product_id_to_product_map.values()


def _generate_context_data(weather_data, start_coords, end_coords):
    context_data = {}
    context_data['weather'] = weather_data
    context_data['start_latitude'] = start_coords.lat
    context_data['start_longitude'] = start_coords.long
    context_data['end_latitude'] = end_coords.lat
    context_data['end_longitude'] = end_coords.long
    return  context_data


def _get_uber_helper(config):
    uber_access_token = config["uber_api"]["debug_access_token"]
    uber_server_token = config["uber_api"]["server_token"]
    uber_client_id = config["uber_api"]["client_id"]
    uber_client_secret = config["uber_api"]["client_secret"]
    uber_helper = UberHelper(uber_server_token, OAuth2Credential(access_token=uber_access_token,
                                                                 client_id=uber_client_id,
                                                                 client_secret=uber_client_secret,
                                                                 expires_in_seconds=999999,
                                                                 scopes={'ride_widgets', 'request'},
                                                                 grant_type=''
                                                                 ))
    return uber_helper


def _get_yahoo_weather_helper(config):
    yahoo_client_id = config["yahoo_weather_api"]["client_id"]
    yahoo_client_secret = config["yahoo_weather_api"]["client_secret"]
    return YahooWeatherHelper(yahoo_client_id, yahoo_client_secret)


def _get_es_connection(config):
    hosts = config['elastic_search']['hosts']
    password = config['elastic_search']['password']
    user_name = config['elastic_search']['user_name']
    port = config['elastic_search']['port']
    return ElasticSearchConnection(hosts=hosts, password=password, user_name=user_name, port=port)


def _fetch_data_for_coords(start_coords, end_coords, config):
    try:
        logger.info("Received coords: ({}, {}), ({}, {})".format(start_coords.lat, start_coords.long, end_coords.lat, end_coords.long))
        timestamp = datetime.datetime.utcnow().isoformat()

        weather_data = _get_yahoo_weather_helper(config).get_weather(start_coords)
        if weather_data is None:
            logger.error("Received None weather data, skipping fetch for coords.")
            return

        uber_helper = _get_uber_helper(config)
        uber_details_list = _get_uber_product_details_list(start_coords, end_coords, uber_helper)

        context_data = _generate_context_data(weather_data, start_coords, end_coords)

        es_connection = _get_es_connection(config)
        ElasticSearchHandler(es_connection, 'uber_prices').push_group(parent_data={'timestamp': timestamp, 'context': context_data},
                                                       parent_doc_type='time_instant_for_coords',
                                                       es_obj_list=uber_details_list,
                                                       doc_type=UberProduct.DOC_TYPE
                                                       )
        logger.info("Successfully pushed coords into elasticsearch index")
    except Exception as e:
        logger.error("An exception occurred: {}".format(e))
        raise


def _setup_logging(verbose):
    module_name_to_logger_map = {'main': logging.getLogger(__name__), 'utils': utils.logger}

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG if verbose else logging.INFO)
    ch.setFormatter(formatter)

    for module_name, module_logger in module_name_to_logger_map.items():
        module_logger.propagate = False
        module_logger.setLevel(logging.DEBUG)

        fh = logging.FileHandler('uber_miner_{}.log'.format(module_name))
        fh.setFormatter(formatter)
        fh.setLevel(logging.DEBUG)

        module_logger.addHandler(ch)
        module_logger.addHandler(fh)


def main():
    response = requests.get('http://serv1.anmolahuja.com/api/get_tracked/')
    logger.debug("Received: {}".format(response.text))
    obj = json.loads(response.text)
    coords_pairs_list = [] #[(apt_coords, symc_coords), (apt_coords, symc_coords)]
    for dic in obj:
        from_latitude = dic['from_latitude']
        from_longitude = dic['from_longitude']
        to_latitude = dic['to_latitude']
        to_longitude = dic['to_longitude']
        print('{},{}; {}, {}'.format(from_latitude, from_longitude, to_latitude, to_longitude))
        coords_pairs_list.append( (Coords(from_latitude, from_longitude), Coords(to_latitude, to_longitude)) )
    #print('{}'.format(coords_pairs_list))

    #apt_coords = Coords(34.024314, -118.297941)
    #symc_coords = Coords(33.988031, -118.388916)

    with open("config.json") as f:
        config = json.load(f, encoding='utf-8')

    IndicesHandler(_get_es_connection(config), 'uber_prices').create_index_if_not_exist()

    while True:
        for pairs in coords_pairs_list:
            _fetch_data_for_coords(pairs[0], pairs[1], config)
        time.sleep(120)


if __name__ == "__main__":
    _setup_logging(verbose=True)
    try:
        main()
    except Exception as e:
        logger.exception(e)
