import json
import os
import tempfile
import time

from elasticsearch import Elasticsearch
import matplotlib.pyplot as plt
import numpy as np
from requests.auth import HTTPDigestAuth
import requests

from django.forms.models import model_to_dict
from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response

from rest_framework.serializers import ModelSerializer

import hermes.settings as settings
from .models import *



@api_view(['PUT'])
#@permission_classes((permissions.AllowAny,))
def create_tracker(request):
    data = request.data

    from_longitude = data['from_longitude']
    from_latitude = data['from_latitude']

    to_longitude = data['to_longitude']
    to_latitude = data['to_latitude']

    id = TrackedCoordinatePairs.generate_id(from_latitude=from_latitude, from_longitude=from_longitude,
                                          to_latitude=to_latitude, to_longitude=to_longitude)
    if not TrackedCoordinatePairs.objects.filter(id=id).exists():
        tpair = TrackedCoordinatePairs.create_tracker(from_latitude=from_latitude, from_longitude=from_longitude,
                                                      to_latitude=to_latitude, to_longitude=to_longitude)
        tpair.save()
    return HttpResponse(json.dumps({'success'}), content_type='application/json')


@api_view(['GET'])
def get_tracked(request):
    serializer = ModelSerializer(TrackedCoordinatePairs.objects.all(), many=True)
    return Response(serializer.data)


@api_view(['GET'])
#@permission_classes((permissions.AllowAny,))
def test_page(request):
    return HttpResponse(json.dumps("Test page"), content_type='application/json')


def _gen_image(start_lat, start_long, end_lat, end_long):
    cur_timestamp = int(time.time()*1000)
    es2 = {
      "query": {
        "bool": {
          "must": [
            {
              "query_string": {
                "analyze_wildcard": True,
                "query": "context.start_latitude={}&context.start_longitude={}&context.end_latitude={}&context.end_longitude={}".format(start_lat, start_long, end_lat, end_long)
              }
            },
            {
              "range": {
                "timestamp": {
                  "gte": 0,
                  "lte": cur_timestamp,
                  "format": "epoch_millis"
                }
              }
            }
          ],
          "must_not": []
        }
      },
      "size": 0,
      "_source": {
        "excludes": []
      },
      "aggs": {
        "2": {
          "date_histogram": {
            "field": "timestamp",
            "interval": "15m",
            "time_zone": "America/Los_Angeles",
            "min_doc_count": 1
          },
          "aggs": {
            "3": {
              "terms": {
                "field": "display_name.keyword",
                "size": 5,
                "order": {
                  "1": "desc"
                }
              },
              "aggs": {
                "1": {
                  "avg": {
                    "field": "high_estimate"
                  }
                }
              }
            }
          }
        }
      }
    }
    config = json.loads(os.path.join('..', 'uber_miner', 'config.json'))

    hosts = config['elastic_search']['hosts']
    password = config['elastic_search']['password']
    user_name = config['elastic_search']['user_name']
    port = config['elastic_search']['port']

    es = Elasticsearch(hosts=hosts, http_auth=(user_name, password), port=port)

    res = es.search(index="uber_prices", body=es2)

    product_to_timevaluetuplelist_map = {}
    for aggregation in res['aggregations']['2']['buckets']:
        buckets = aggregation['3']['buckets']
        timestamp = aggregation['key']
        for bucket in buckets:
            product = bucket['key']
            price = bucket['1']['value']
            if product not in product_to_timevaluetuplelist_map:
                product_to_timevaluetuplelist_map[product] = []
            product_to_timevaluetuplelist_map[product].append((timestamp, price))

    fig = plt.figure()
    colors = ('b', 'g', 'r', 'c', 'm', 'y', 'k') # TODO: don't hardcode
    patches = []

    for i, product in enumerate(product_to_timevaluetuplelist_map.keys()):
        l = product_to_timevaluetuplelist_map[product]
        color = colors[i]
        import matplotlib.patches as mpatches
        patches.append(mpatches.Patch(color=color, label=product))
        plt.plot([x[0] for x in l], [x[1] for x in l], color=color)
    plt.legend(handles=patches)


    with tempfile.NamedTemporaryFile(mode='w+b', delete=False, suffix='.png') as f:
        file_name = f.name

    fig.savefig(file_name)
    return file_name


@api_view(['GET'])
#@permission_classes((permissions.AllowAny,))
def get_graph(request):
    import time
    data = request.data
    file_name = _gen_image(data['start_latitude'], data['start_longitude'], data['end_latitude'], data['end_longitude'])
    with open(file_name, "rb") as f:
        return HttpResponse(f.read(), content_type="image/jpeg")
