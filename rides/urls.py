# API For drivers to create rides
# API For passengers to find rides
# API For passengers to request rides
# API For drivers to manage requests
# API For updating ride location
# API For completing rides
# API For post-ride ratings

from django.urls import path
from .views import (CreateRideView,FindRidesView)
from rides.consumers import RideLocationConsumer
urlpatterns = [
    path('create/', CreateRideView.as_view(), name='create_ride'),
    path('find/', FindRidesView.as_view(), name='find_rides'),
    
]

