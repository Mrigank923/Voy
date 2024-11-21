from django.urls import path

from rides.consumers import ChatConsumer, RideLocationConsumer

# Define your WebSocket URL patterns here
websocket_urlpatterns = [
    path("ws/rides/<int:ride_id>/location/", RideLocationConsumer.as_asgi()),
    path("ws/chat/<str:room_name>/", ChatConsumer.as_asgi()),
]
