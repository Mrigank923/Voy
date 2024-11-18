from channels.generic.websocket import AsyncWebsocketConsumer
import json
from django.contrib.gis.geos import Point
from .models import RideDetails
from channels.auth import AuthMiddlewareStack
from rides import consumers

class RideLocationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Get the ride ID from the URL
        self.ride_id = self.scope['url_route']['kwargs']['ride_id']
        self.ride_group_name = f"ride_{self.ride_id}"

        # Join the group
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
        try:
            # Receive location data sent from the WebSocket client
            data = json.loads(text_data)
            latitude = data.get('latitude')
            longitude = data.get('longitude')
            
            if latitude is None or longitude is None:
                raise ValueError("Missing latitude or longitude")

            # Update the ride's location 
            try:
                ride = RideDetails.objects.get(id=self.ride_id)
                ride.start_point = Point(longitude, latitude, srid=4326)
                ride.save()
            except RideDetails.DoesNotExist:
                # If the ride is not found, send an error message and close the connection
                await self.send(text_data=json.dumps({"error": "Ride not found"}))
                return

            # Send the updated location to all clients in the group
            await self.channel_layer.group_send(
                self.ride_group_name,
                {
                    'type': 'send_location',
                    'latitude': latitude,
                    'longitude': longitude
                }
            )
        except ValueError as e:
            # Handle missing latitude or longitude
            await self.send(text_data=json.dumps({"error": str(e)}))
        except Exception as e:
            # Handle general exceptions
            print(f"Error in receive method: {e}")
            await self.send(text_data=json.dumps({"error": "An error occurred processing the data"}))

    async def send_location(self, event):
        # Send the updated location to WebSocket client
        await self.send(text_data=json.dumps({
            'latitude': event['latitude'],
            'longitude': event['longitude']
        }))



class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Get the room name from the URL parameters
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f"chat_{self.room_name}"

        # Join the room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Leave the room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        # Receive chat message from WebSocket client
        data = json.loads(text_data)
        message = data['message']

        # Send the message to all clients in the group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message
            }
        )

    async def chat_message(self, event):
        # Send the chat message to WebSocket client
        await self.send(text_data=json.dumps({
            'message': event['message']
        }))
