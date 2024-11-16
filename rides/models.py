from django.db import models
from authentication.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.gis.db import models



# models that we will be needing for the rides app
# RideDetails model will be used to store the details of a ride
# PassengerRideRequest model will be used to store the details of a passenger's ride request
#TODO A rideParticipants model to track the passengers in each ride
#TODO A model for locations, as the location will be uppdated in real time
#TODO A model for user ratings, make sure to implement weighted rating

#FIXME use GeoDjango and postGis for storing coordinates and do calculations on the coordinates

class RideDetails(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('ONGOING', 'Ongoing'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled')
    ]

    driver = models.ForeignKey(User,on_delete=models.CASCADE,related_name='driver_rides')
    start_location = models.CharField(max_length=255)
    end_location = models.CharField(max_length=255)
    start_point = models.PointField(srid=4326, null=True, blank=True)
    end_point = models.PointField(srid=4326, null=True, blank=True)
    route_line = models.LineStringField(srid=4326,null=True,blank=True)
    start_time = models.DateTimeField()
    available_seats = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(8)])
    status = models.CharField(max_length=20,choices=STATUS_CHOICES,default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'start_time']),
            models.Index(fields=['driver', 'status'])
        ]


class PassengerRideRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
        ('REJECTED', 'Rejected'),
        ('IN_VEHICLE', 'In Vehicle'),
        ('COMPLETED', 'Completed')
    ]

    passenger = models.ForeignKey(User,on_delete=models.CASCADE,related_name='Passenger_ride_requests')
    ride = models.ForeignKey(RideDetails,on_delete=models.CASCADE,related_name='requests' )
    pickup_location = models.CharField(max_length=255)
    dropoff_location = models.CharField(max_length=255)
    pickup_point = models.PointField(srid=4326, null=True, blank=True)
    dropoff_point = models.PointField(srid=4326, null=True, blank=True)
    seats_needed = models.PositiveIntegerField(default=1,validators=[MinValueValidator(1), MaxValueValidator(8)])
    status = models.CharField(max_length=20,choices=STATUS_CHOICES,default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'ride']),
            models.Index(fields=['passenger', 'status'])
        ]


