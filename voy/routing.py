

from django.urls import path
from rides.consumers import RideLocationConsumer


websocket_urlpatterns = [
    path("ws/rides/<int:ride_id>/location/", RideLocationConsumer.as_asgi()), 
]
