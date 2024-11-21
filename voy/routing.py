from django.urls import path

from rides.consumers import RideChatConsumer, RideLocationConsumer

# Define your WebSocket URL patterns here
websocket_urlpatterns = [
    path("ws/rides/<int:ride_id>/location/", RideLocationConsumer.as_asgi()),
    path('ws/ride/<int:ride_id>/chat/', RideChatConsumer.as_asgi()),
]
