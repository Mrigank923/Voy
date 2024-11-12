from django.db import models
from authentication.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

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

    driver = models.ForeignKey(User,on_delete=models.CASCADE,related_name='driver_rides'
)
    start_location = models.CharField(max_length=200)
    end_location = models.CharField(max_length=200)
    start_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    start_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    end_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    end_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    start_time = models.DateTimeField()
    available_seats = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(4)]
    )
    status = models.CharField(max_length=20,choices=STATUS_CHOICES,default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']


class PassengerRideRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
        ('REJECTED', 'Rejected')
    ]

    passenger = models.ForeignKey(User,on_delete=models.CASCADE,related_name='Passenger_ride_requests')
    ride = models.ForeignKey(RideDetails,on_delete=models.CASCADE,related_name='requests' )
    pickup_location = models.CharField(max_length=255)
    dropoff_location = models.CharField(max_length=255)
    pickup_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    pickup_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    dropoff_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    dropoff_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    seats_needed = models.PositiveIntegerField(default=1,validators=[MinValueValidator(1), MaxValueValidator(8)])
    status = models.CharField(max_length=20,choices=STATUS_CHOICES,default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']


