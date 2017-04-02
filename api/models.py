from __future__ import unicode_literals

# Create your models here.
from django.contrib.auth.models import User
from django.db import models


class TrackedCoordinatePairs(models.Model):
    id = models.CharField(max_length=200, primary_key=True)

    from_latitude = models.FloatField()
    from_longitude = models.FloatField()

    to_longitude = models.FloatField()
    to_latitude = models.FloatField()

    def create_tracker(self, from_latitude, from_longitude, to_latitude, to_longitude):
        id = '{},{},{},{}'.format(from_latitude, from_longitude,
                                  to_latitude, to_longitude)
        self.objects.create(id=id, from_latitude=from_latitude, from_longitude=from_longitude,
                            to_longitude=to_longitude, to_latitude=to_latitude)
    #class Meta:
    #    app_label = 'hermesapi'
