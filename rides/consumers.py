import json
import re
from datetime import datetime

from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from channels.exceptions import StopConsumer
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.contrib.gis.geos import Point
from django.utils import timezone

from rides import consumers
from rides.models import ChatMessage, PassengerRideRequest, RideDetails

from .models import RideDetails

User = get_user_model()

class RideLocationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]

        # Ensure user is authenticated
        if not self.user.is_authenticated:
            await self.close()
            return

        # Extract ride ID from URL
        self.ride_id = self.scope["url_route"]["kwargs"]["ride_id"]

        print(f"User {self.user.email} attempting to connect to ride {self.ride_id}")

        # Validate ride access
        access_details = await self.get_ride_access_details()
        if not access_details['has_access']:
            print(f"Access Denied for user {self.user.email} to ride {self.ride_id}")
            await self.close()
            return

        self.is_driver = access_details['is_driver']
        self.room_group_name = f"ride_location_{self.ride_id}"

        print(f"User {self.user.email} connecting to room {self.room_group_name}")

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    @database_sync_to_async
    def get_ride_access_details(self):
        """
        Validate user access to the ride location updates.
        """
        try:
            ride = RideDetails.objects.get(id=self.ride_id)

            # Check if the user is the driver
            if ride.driver == self.user:
                print(f"User {self.user.email} is the driver of ride {self.ride_id}")
                return {'has_access': True, 'is_driver': True}

            # Check if the user is a confirmed passenger
            passenger_request = PassengerRideRequest.objects.filter(
                ride=ride,
                passenger=self.user,
                status__in=['CONFIRMED', 'IN_VEHICLE']
            ).first()
            if passenger_request:
                print(f"User {self.user.email} is a confirmed passenger of ride {self.ride_id}")
                return {'has_access': True, 'is_driver': False}

            print(f"User {self.user.email} is neither the driver nor a confirmed passenger of ride {self.ride_id}")
            return {'has_access': False, 'is_driver': False}

        except RideDetails.DoesNotExist:
            print(f"Ride {self.ride_id} does not exist")
            return {'has_access': False, 'is_driver': False}

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
            print(f"User {self.user.email} disconnected from room {self.room_group_name}")

    async def receive(self, text_data):
        data = json.loads(text_data)
        latitude = data.get("latitude")
        longitude = data.get("longitude")

        print(f"Received location update from user {self.user.email}: {latitude}, {longitude}")

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "location_message",
                "latitude": latitude,
                "longitude": longitude,
                "user_id": self.user.id,
                "user_email": self.user.email,
            }
        )

    async def location_message(self, event):
        await self.send(text_data=json.dumps({
            "latitude": event["latitude"],
            "longitude": event["longitude"],
            "user_id": event["user_id"],
            "user_email": event["user_email"],
        }))




User = get_user_model()

class RideChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]

        # Ensure user is authenticated
        if not self.user.is_authenticated:
            await self.close()
            return

        # Extract ride ID and partner ID from URL
        self.ride_id = self.scope["url_route"]["kwargs"]["ride_id"]
        self.partner_id = self.scope["url_route"]["kwargs"]["partner_id"]

        print(f"User {self.user.id} attempting to connect to ride {self.ride_id} with partner {self.partner_id}")

        # Validate chat access
        chat_details = await self.get_chat_details()
        if not chat_details['has_access']:
            print(f"Access denied for user {self.user.id} to ride {self.ride_id}")
            await self.close()
            return

        self.is_driver = chat_details['is_driver']

        # Create room group name for each driver-passenger pair
        self.room_group_name = f"chat_ride_{self.ride_id}_user_{min(self.user.id, self.partner_id)}_{max(self.user.id, self.partner_id)}"

        print(f"User {self.user.id} connecting to room {self.room_group_name}")

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

        # Notify about the connection
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": f"{'Driver' if self.is_driver else 'Passenger'} connected",
                "user_id": self.user.id,
                
                "timestamp": timezone.now().isoformat()
            }
        )

    @database_sync_to_async
    def get_chat_details(self):
        """
        Validate user access to the ride chat and determine the chat partner.
        """
        try:
            ride = RideDetails.objects.get(id=self.ride_id)
            partner = User.objects.get(id=self.partner_id)

            # Check if the user is the driver and the partner is a confirmed passenger
            if ride.driver == self.user:
                passenger_request = PassengerRideRequest.objects.filter(
                    ride=ride,
                    passenger=partner,
                    status__in=['CONFIRMED', 'IN_VEHICLE']
                ).first()
                if passenger_request:
                    print(f"Driver {self.user.id} found confirmed passenger {partner.id} for ride {self.ride_id}")
                    return {'has_access': True, 'is_driver': True}
                else:
                    print(f"No confirmed or in-vehicle passenger found for driver {self.user.id} and partner {partner.id}")

            # Check if the user is a confirmed passenger and the partner is the driver
            if partner == ride.driver:
                passenger_request = PassengerRideRequest.objects.filter(
                    ride=ride,
                    passenger=self.user,
                    status__in=['CONFIRMED', 'IN_VEHICLE']
                ).first()
                if passenger_request:
                    print(f"Passenger {self.user.id} confirmed for ride {self.ride_id} with driver {partner.id}")
                    return {'has_access': True, 'is_driver': False}
                else:
                    print(f"No confirmed or in-vehicle status for passenger {self.user.id} in ride {self.ride_id}")

            print(f"Access denied: user {self.user.id} is not the driver or a confirmed passenger in ride {self.ride_id}")
            return {'has_access': False, 'is_driver': False}

        except RideDetails.DoesNotExist:
            print(f"Ride {self.ride_id} does not exist")
            return {'has_access': False, 'is_driver': False}

        except User.DoesNotExist:
            print(f"Partner {self.partner_id} does not exist")
            return {'has_access': False, 'is_driver': False}

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            # Notify about the disconnection
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "message": f"{'Driver' if self.is_driver else 'Passenger'} disconnected",
                    "user_id": self.user.id,
                    
                    "timestamp": timezone.now().isoformat()
                }
            )

            # Leave room group
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
            print(f"User {self.user.id} disconnected from room {self.room_group_name}")

    async def receive(self, text_data):
        try:
            # Parse incoming data
            data = json.loads(text_data)
            message = data.get("message", "").strip()

            # Validate message length and content
            if not message or len(message) > 1000:
                return  # Ignore invalid messages

            print(f"Received message from user {self.user.id}: {message}")

            # Save the message to the database
            await self.save_message(message)

            # Broadcast the message to the group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "message": message,
                    "user_id": self.user.id,
                    
                    "timestamp": timezone.now().isoformat()
                }
            )

        except json.JSONDecodeError:
            print("Invalid JSON received")
            await self.send(json.dumps({"error": "Invalid message format"}))
        except Exception as e:
            print(f"Error in receive: {e}")

    @database_sync_to_async
    def save_message(self, message):
        """
        Save the message to the database.
        """
        ChatMessage.objects.create(
            ride_id=self.ride_id,
            sender=self.user,
            receiver_id=self.partner_id,
            message=message
        )
        print(f"Message saved to database: {message[:50]}...")

    async def chat_message(self, event):
        """
        Handle broadcasting messages to WebSocket clients.
        """
        sender_email = await self.get_user_email(event["user_id"])

        # Send the message to WebSocket
        await self.send(json.dumps({
            "message": event["message"],
            "user_id": event["user_id"],
            "user_email": sender_email,
            
            "timestamp": event["timestamp"]
        }))

    @database_sync_to_async
    def get_user_email(self, user_id):
        """
        Retrieve the user's email address by ID.
        """
        try:
            user = User.objects.get(id=user_id)
            return user.email
        except User.DoesNotExist:
            return "Unknown"
