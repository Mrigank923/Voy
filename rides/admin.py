from django.contrib import admin
from rides.models import RideDetails,PassengerRideRequest,Rating, ChatMessage


# Register your models here.



admin.site.register(RideDetails)
admin.site.register(PassengerRideRequest)
admin.site.register(Rating)
admin.site.register( ChatMessage)