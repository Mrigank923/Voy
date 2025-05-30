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

    def __str__(self):
        return f"Ride from {self.start_location} to {self.end_location} by {self.driver.email} on {self.start_time.strftime('%Y-%m-%d %H:%M')}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def calculate_distance(self):
        if self.start_point and self.end_point:
            return self.start_point.distance(self.end_point) * 100  # Convert to kilometers
        return 0

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "start_time"]),
            models.Index(fields=["driver", "status"]),
        ]
        verbose_name = 'Ride Detail'
        verbose_name_plural = 'Ride Details'


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
    payment_completed = models.BooleanField(default=False, null=True)
    
    def __str__(self):
        return f"Request by {self.passenger.email} for {self.seats_needed} seat(s) - {self.status}"

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

    def __str__(self):
        return f"{self.from_user.email}'s {self.score}-star rating to {self.to_user.email}"
    class Meta:
        unique_together = ["ride", "from_user", "to_user"]


# models.py
class ChatMessage(models.Model):
    ride = models.ForeignKey(RideDetails, on_delete=models.CASCADE)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.sender.email} to {self.receiver.email} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
    
    class Meta:
        ordering = ['timestamp']