from channels.generic.websocket import AsyncWebsocketConsumer
import json
from django.contrib.gis.geos import Point
from .models import RideDetails




class RideLocationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Get the ride ID from the URL
        self.ride_id = self.scope['url_route']['kwargs']['ride_id']
        self.ride_group_name = f"ride_{self.ride_id}"

        
        await self.channel_layer.group_add(
            self.ride_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Leave the group when disconnected
        await self.channel_layer.group_discard(
            self.ride_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        # Receive location data sent from the WebSocket client
        data = json.loads(text_data)
        latitude = data['latitude']
        longitude = data['longitude']
        
        # Update the ride's location 
        ride = RideDetails.objects.get(id=self.ride_id)
        ride.start_point = Point(longitude, latitude, srid=4326)
        ride.save()

        # Send the updated location to all clients in the group
        await self.channel_layer.group_send(
            self.ride_group_name,
            {
                'type': 'send_location',
                'latitude': latitude,
                'longitude': longitude
            }
        )

    async def send_location(self, event):
        # Send the updated location to WebSocket client
        await self.send(text_data=json.dumps({
            'latitude': event['latitude'],
            'longitude': event['longitude']
        }))
