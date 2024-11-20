from django.contrib.gis.db import models
from django.core.validators import MaxValueValidator, MinValueValidator

from authentication.models import User


class RideDetails(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("ONGOING", "Ongoing"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    ]

    driver = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="driver_rides"
    )
    start_location = models.CharField(max_length=255)
    end_location = models.CharField(max_length=255)
    start_point = models.PointField(srid=4326, null=True, blank=True)
    end_point = models.PointField(srid=4326, null=True, blank=True)
    route_line = models.LineStringField(srid=4326, null=True, blank=True)
    start_time = models.DateTimeField()
    available_seats = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(8)]
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "start_time"]),
            models.Index(fields=["driver", "status"]),
        ]


class PassengerRideRequest(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("CONFIRMED", "Confirmed"),
        ("CANCELLED", "Cancelled"),
        ("REJECTED", "Rejected"),
        ("IN_VEHICLE", "In Vehicle"),
        ("COMPLETED", "Completed"),
    ]

    passenger = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="Passenger_ride_requests"
    )
    ride = models.ForeignKey(
        RideDetails, on_delete=models.CASCADE, related_name="requests"
    )
    pickup_location = models.CharField(max_length=255)
    dropoff_location = models.CharField(max_length=255)
    pickup_point = models.PointField(srid=4326, null=True, blank=True)
    dropoff_point = models.PointField(srid=4326, null=True, blank=True)
    seats_needed = models.PositiveIntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(8)]
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "ride"]),
            models.Index(fields=["passenger", "status"]),
        ]


class Rating(models.Model):
    ride = models.ForeignKey("RideDetails", on_delete=models.CASCADE)
    from_user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="ratings_given"
    )
    to_user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="ratings_received"
    )
    score = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["ride", "from_user", "to_user"]
