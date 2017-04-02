import collections
import logging
import requests

from elasticsearch import client, helpers, Elasticsearch, RequestsHttpConnection

logger = logging.getLogger(__name__)


class ElasticSearchHandler(object):
    def __init__(self, es_connection, index_name):
        self.index_name = index_name
        self.conn = es_connection

    def push_group(self, parent_data, parent_doc_type, es_obj_list, doc_type, refresh=True):
        """ Assumes objects do NOT have an id."""
        parent_doc_id = self.push(parent_data, doc_type=parent_doc_type, refresh=refresh)
        if parent_doc_id is None:
            raise RuntimeError("Failed to create parent doc")
        es_repr_list = []
        for es_obj in es_obj_list:
            doc_type, es_repr = self._validate_doc_and_get_type_and_repr(es_obj, doc_type)
            es_repr.update(parent_data)
            es_repr['parent_id'] = parent_doc_id
            es_repr_list.append(es_repr)
        self.push_bulk(es_repr_list, doc_type, refresh)

    def push_bulk(self, obj_list, doc_type=None, refresh=True):
        """ Assumes objects do NOT have an id.
        :param obj_list:
        :param doc_type:
        :param refresh:
        :return:
        """
        assert isinstance(obj_list, collections.Sequence)
        assert len(obj_list) > 0

        es_obj_list = []
        for obj in obj_list:
            if obj is None:
                logger.warning("None object in input list")
                continue

            doc_type, es_repr = self._validate_doc_and_get_type_and_repr(obj, doc_type)
            metadata = {
                '_op_type': 'index',
                "_index": self.index_name,
                "_type": doc_type,
            }
            es_repr.update(**metadata)

            es_obj_list.append(es_repr)

        helpers.bulk(client=self.conn.elastic_search_client, actions=es_obj_list,
                                             stats_only=True, refresh=u'true' if refresh else u'false')

    def push(self, es_obj, doc_type=None, refresh=True):
        """ Push a single ElasticSearchObject to index. Assumes objects do NOT have an id.

        Returns:
            id of the created document if successful, None otherwise
        """
        doc_type, es_repr = self._validate_doc_and_get_type_and_repr(es_obj, doc_type)
        response = self.conn.elastic_search_client.index(index=self.index_name, doc_type=doc_type,
                                           body=es_repr, refresh=u'true' if refresh else u'false', id=None)
        logger.debug("Response: {}".format(response))
        print(response)
        if '_id' not in response:
            logger.error("Could not create object")
            logger.error("Object: {}".format(es_obj))
            logger.error("Es_repr: {}".format(es_repr))
            logger.error("Response: {}".format(response))
            return None
        id = response['_id']
        return id

    def _validate_doc_and_get_type_and_repr(self, es_obj, doc_type):
        if isinstance(es_obj, ElasticSearchDoc):
            assert doc_type is None or doc_type == es_obj.doc_type()
            return es_obj.doc_type(), es_obj.elastic_search_representation()

        assert isinstance(es_obj, (collections.Sequence, collections.Mapping))
        assert doc_type is not None
        return doc_type, es_obj


class IndicesHandler(object):
    def __init__(self, elastic_search_connection, index_name):
        self.index_name = index_name
        self.indices_client = client.IndicesClient(elastic_search_connection.elastic_search_client)

    def index_exists(self):
        return self.indices_client.exists(self.index_name)

    def create_index(self):
        """ Recreate the index. Warning, deletes and recreates it, all existing data will be wiped
        """
        if self.index_exists():
            logger.info('Index {} already exists'.format(self.index_name))
            logger.info('Deleting existing index')
            self.indices_client.delete(index=self.index_name)
        self.create_index_if_not_exist()

    def create_index_if_not_exist(self):
        if self.index_exists():
            return
        logger.info('Creating index {}'.format(self.index_name))
        self.indices_client.create(index=self.index_name)

    def create_mappings(self, doctype_to_mapping_map):
        logger.info('Creating mappings')
        for doc_type, mapping in doctype_to_mapping_map.items():
            logger.info('Creating mapping for doctype "{}"'.format(doc_type))
            self.indices_client.put_mapping(
                doc_type=doc_type,
                body=mapping,
                index=self.index_name
            )


class ElasticSearchConnection:
    def __init__(self, hosts, port, user_name, password, connection_class=RequestsHttpConnection):
        """ Uses http for now.
        """
        self.hosts = hosts
        self.connection_class = connection_class
        self.elastic_search_client = Elasticsearch(self.hosts, connection_class=self.connection_class)
        self.elastic_search_client = Elasticsearch(hosts, http_auth=(user_name, password), port=port)


class ElasticSearchDoc(object):
    def doc_type(self):
        raise NotImplementedError()

    def elastic_search_representation(self):
        raise NotImplementedError()
