from channels.generic.websocket import AsyncWebsocketConsumer
import json
from django.contrib.gis.geos import Point
from .models import RideDetails
from channels.auth import AuthMiddlewareStack
from rides import consumers
from rides.models import  PassengerRideRequest,RideDetails

from channels.exceptions import StopConsumer
from channels.db import database_sync_to_async

from channels.generic.websocket import AsyncWebsocketConsumer
import re


from datetime import datetime
from django.contrib.gis.geos import Point






class RideLocationConsumer(AsyncWebsocketConsumer):
    @database_sync_to_async
    def validate_ride_access(self, user, ride_id):
        """
        Validate whether the user has access to the specified ride.
        """
        is_driver = RideDetails.objects.filter(id=ride_id, driver=user).exists()
        is_confirmed_passenger = PassengerRideRequest.objects.filter(
            ride_id=ride_id, passenger=user, status='CONFIRMED'
        ).exists()
        return is_driver or is_confirmed_passenger

    @database_sync_to_async
    def update_ride_location(self, ride_id, latitude, longitude):
        """
        Update the ride's location with new latitude and longitude.
        """
        try:
            ride = RideDetails.objects.get(id=ride_id)
            ride.start_point = Point(longitude, latitude, srid=4326)
            ride.save()
            return True
        except RideDetails.DoesNotExist:
            return False

    async def connect(self):
        user = self.scope["user"]

        # Check if user is authenticated
        if not user.is_authenticated:
            await self.close(code=4001)  
            return

        # Get ride_id from URL and validate access
        self.ride_id = self.scope["url_route"]["kwargs"]["ride_id"]
        if not await self.validate_ride_access(user, self.ride_id):
            await self.close(code=4003)  
            return

        # Join the ride group
        self.ride_group_name = f"ride_{self.ride_id}"
        await self.channel_layer.group_add(self.ride_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'ride_group_name'):
            await self.channel_layer.group_discard(self.ride_group_name, self.channel_name)
        raise StopConsumer()

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            latitude = data.get("latitude")
            longitude = data.get("longitude")

            # Validate latitude and longitude
            if not (-90 <= float(latitude) <= 90 and -180 <= float(longitude) <= 180):
                raise ValueError("Invalid coordinates")

            # Update ride location
            updated = await self.update_ride_location(self.ride_id, latitude, longitude)
            if not updated:
                await self.send(json.dumps({"type": "error", "message": "Ride not found"}))
                await self.close(code=4004)
                return

            #  location update 
            timestamp = datetime.now().isoformat()
            user_email = self.scope["user"].email
            await self.channel_layer.group_send(
                self.ride_group_name,
                {
                    "type": "send_location",
                    "latitude": latitude,
                    "longitude": longitude,
                    "timestamp": timestamp,
                    "user_email": user_email,
                }
            )

        except json.JSONDecodeError:
            await self.send(json.dumps({"type": "error", "message": "Invalid JSON format"}))
        except ValueError as e:
            await self.send(json.dumps({"type": "error", "message": str(e)}))
        except Exception as e:
            print(f"Error in receive: {e}")
            await self.send(json.dumps({"type": "error", "message": "An error occurred"}))

    async def send_location(self, event):
        """
        Send location updates to WebSocket clients.
        """
        await self.send(json.dumps({
            "type": "location_update",
            "latitude": event["latitude"],
            "longitude": event["longitude"],
            "timestamp": event["timestamp"],
            "user_email": event["user_email"]
        }))






class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Get and validate room name
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        
        # Basic validation of room name 
        if not re.match("^[a-zA-Z0-9_-]+$", self.room_name) or len(self.room_name) > 50:
            await self.close()
            return
            
        self.room_group_name = f"chat_{self.room_name}"

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        try:
            #  received data
            data = json.loads(text_data)
            message = data.get('message', '').strip()
            username = data.get('username')

            # Validate message
            if not message or len(message) > 1000:  
                return

            # Get the user's email and timestamp
            user_email = self.scope["user"].email  
            timestamp = datetime.now().isoformat()  

            # Send message to room group 
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'username': username,
                    'user_email': user_email,  
                    'timestamp': timestamp  
                }
            )

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'error': 'Invalid message format'
            }))
        except Exception as e:
            print(f"Error in receive: {e}")

    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'username': event['username'],
            'user_email': event['user_email'],  
            'timestamp': event['timestamp']  
        }))
