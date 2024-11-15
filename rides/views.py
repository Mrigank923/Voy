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
            destination_point = request.query_params.get('destination_point')
            if not destination_point:
                return Response(
                    {"error": "destination_point parameter is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Parse GeoJSON point
            point_data = json.loads(destination_point)
            coords = point_data['coordinates']
            end_point = Point(coords[0], coords[1], srid=4326)
            
            # Get search radius (default 5km)
            search_radius = float(request.query_params.get('radius', 5000))

            available_rides = RideDetails.objects.filter(
                status='PENDING',
                available_seats__gte=1
            ).annotate(
                distance_to_destination=Distance('end_point', end_point)
            ).filter(
                distance_to_destination__lte=D(m=search_radius)
            ).order_by('start_time')

            serializer = RideDetailsSerializer(available_rides, many=True)
            return Response(serializer.data)

        except (json.JSONDecodeError, ValueError) as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

class CreateRideRequestView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, ride_id):
        try:
            ride = get_object_or_404(RideDetails, id=ride_id, status='PENDING')
            
            # Check if user already has a pending request for this ride
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
            
            ride_request = PassengerRideRequest.objects.create(
                passenger=request.user,
                ride=ride,
                seats_needed=seats_needed,
                status='PENDING'
            )
            
            serializer = PassengerRideRequestSerializer(ride_request)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except RideDetails.DoesNotExist:
            return Response(
                {"error": "Ride not found"},
                status=status.HTTP_404_NOT_FOUND
            )

class ListRideRequestsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, ride_id):
        # Ensure the user is the driver of the ride
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

