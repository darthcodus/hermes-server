from __future__ import unicode_literals

# Create your models here.
from django.contrib.auth.models import User
from django.db import models

from rest_framework import serializers


class TrackedCoordinatePairs(models.Model):
    id = models.CharField(max_length=200, primary_key=True)

    from_latitude = models.FloatField()
    from_longitude = models.FloatField()

    to_longitude = models.FloatField()
    to_latitude = models.FloatField()

    @classmethod
    def generate_id(cls, from_latitude, from_longitude, to_latitude, to_longitude):
        id = '{},{},{},{}'.format(from_latitude, from_longitude,to_latitude, to_longitude)
        return id

    @classmethod
    def create_tracker(cls, from_latitude, from_longitude, to_latitude, to_longitude, id=None):
        if id is None:
            id = cls.generate_id(from_latitude, from_longitude, to_latitude, to_longitude)
        return cls.objects.create(id=id, from_latitude=from_latitude, from_longitude=from_longitude,
                            to_longitude=to_longitude, to_latitude=to_latitude)
    #class Meta:
    #    app_label = 'hermesapi'

class TrackedCoordsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrackedCoordinatePairs
        fields = ('id', 'from_latitude', 'from_longitude', 'to_latitude', 'to_longitude')

