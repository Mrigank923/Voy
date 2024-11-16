from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.gis.db.models.functions import Distance
from django.shortcuts import get_object_or_404
from django.contrib.gis.measure import D
from .models import RideDetails, PassengerRideRequest
from .serializers import RideDetailsSerializer, PassengerRideRequestSerializer
from rest_framework import serializers
import json
from django.contrib.gis.geos import Point
from rest_framework.views import APIView

class CreateRideView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = RideDetailsSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(driver=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class FindRidesView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            #search params
            pickup_point = json.loads(request.query_params.get('pickup_point'))
            destination_point = json.loads(request.query_params.get('destination_point'))
            seats_needed = int(request.query_params.get('seats_needed', 1))
            search_radius = float(request.query_params.get('radius', 5000))  # 5km default
            
            # Convert to Django Point objects
            pickup = Point(pickup_point['coordinates'][0], pickup_point['coordinates'][1], srid=4326)
            destination = Point(destination_point['coordinates'][0], destination_point['coordinates'][1], srid=4326)
            
            available_rides = RideDetails.objects.filter(
                status='PENDING',
                available_seats__gte=seats_needed
            ).annotate(
                distance_to_pickup=Distance('start_point', pickup),
                distance_to_destination=Distance('end_point', destination)
            ).filter(
                distance_to_pickup__lte=D(m=search_radius),
                distance_to_destination__lte=D(m=search_radius)
            ).order_by('start_time')

            serializer = RideDetailsSerializer(available_rides, many=True)
            return Response(serializer.data)

        except (json.JSONDecodeError, ValueError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CreateRideRequestView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, ride_id):
        try:
            ride = get_object_or_404(RideDetails, id=ride_id, status='PENDING')
            
            #does a pending request already exist for this ride?
            existing_request = PassengerRideRequest.objects.filter(
                passenger=request.user,
                ride=ride,
                status='PENDING'
            ).exists()
            
            if existing_request:
                return Response(
                    {"error": "You already have a pending request for this ride"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            seats_needed = request.data.get('seats_needed', 1)
            if seats_needed > ride.available_seats:
                return Response(
                    {"error": f"Only {ride.available_seats} seats available"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            request_data = {
                'ride': ride_id,
                'seats_needed': seats_needed,
                'pickup_location': request.data.get('pickup_location'),
                'dropoff_location': request.data.get('dropoff_location'),
                'pickup_point': request.data.get('pickup_point'),
                'dropoff_point': request.data.get('dropoff_point')
            }
            
            serializer = PassengerRideRequestSerializer(data=request_data)
            if serializer.is_valid():
                serializer.save(passenger=request.user)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except RideDetails.DoesNotExist:
            return Response(
                {"error": "Ride not found"},
                status=status.HTTP_404_NOT_FOUND
            )

class ListRideRequestsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, ride_id):
        # make sure the user is the driver of the ride
        ride = get_object_or_404(RideDetails, id=ride_id, driver=request.user)
        
        requests = PassengerRideRequest.objects.filter(
            ride=ride,
            status='PENDING'
        )
        
        serializer = PassengerRideRequestSerializer(requests, many=True)
        return Response(serializer.data)

class ManageRideRequestView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, request_id):
        ride_request = get_object_or_404(PassengerRideRequest, id=request_id)
        
        if request.user != ride_request.ride.driver:
            return Response(
                {"error": "You are not authorized to manage this request"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        action = request.data.get('action')
        if action not in ['accept', 'reject']:
            return Response(
                {"error": "Invalid action. Use 'accept' or 'reject'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        ride = ride_request.ride
        
        if action == 'accept':
            if ride_request.seats_needed > ride.available_seats:
                return Response(
                    {"error": f"Only {ride.available_seats} seats available"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            ride_request.status = 'CONFIRMED'
            ride.available_seats -= ride_request.seats_needed
            
        else:  
            ride_request.status = 'REJECTED'
        
        ride_request.save()
        ride.save()
        
        return Response({
            "message": f"Request {action}ed successfully",
            "available_seats": ride.available_seats
        })

class RideStatusView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, ride_id):
        ride = get_object_or_404(RideDetails, id=ride_id)
        
        # Ensure user is the driver
        if request.user != ride.driver:
            return Response(
                {"error": "Only the driver can update ride status"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        new_status = request.data.get('status')
        if new_status not in ['ONGOING', 'COMPLETED', 'CANCELLED']:
            return Response(
                {"error": "Invalid status"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update ride status
        ride.status = new_status
        ride.save()
        
        # Update all confirmed requests if ride is completed or cancelled
        if new_status in ['COMPLETED', 'CANCELLED']:
            ride.requests.filter(status='CONFIRMED').update(status=new_status)
        
        return Response({"message": f"Ride status updated to {new_status}"})
    

class PassengerStatusView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, request_id):
        ride_request = get_object_or_404(PassengerRideRequest, 
                                       id=request_id,
                                       passenger=request.user)
        
        new_status = request.data.get('status')
        if new_status != 'IN_VEHICLE':
            return Response(
                {"error": "Invalid status"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        ride_request.status = new_status
        ride_request.save()
        
        return Response({"message": "Status updated to IN_VEHICLE"})