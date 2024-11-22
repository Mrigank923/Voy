from django.urls import path

from rides.consumers import RideChatConsumer, RideLocationConsumer

# Define your WebSocket URL patterns here
websocket_urlpatterns = [
    path("ws/rides/<int:ride_id>/location/", RideLocationConsumer.as_asgi()),
    path("ws/ride-chat/<int:ride_id>/<int:partner_id>/",RideChatConsumer.as_asgi()),

]
