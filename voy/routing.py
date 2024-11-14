

from django.urls import path
from rides.consumers import RideConsumer  #

websocket_urlpatterns = [
    path("ws/ride/<int:ride_id>/", RideConsumer.as_asgi()), 
]
