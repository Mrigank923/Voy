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
from .serializers import RideDetailsSerializer, RideSearchSerializer, RideRequestSerializer, RideActionSerializer, RideStatusSerializer, PassengerStatusSerializer
from .serializers import RideHistorySerializer, EmissionsSavingsSerializer
from rest_framework import serializers
import json
from django.contrib.gis.geos import Point
from rest_framework.views import APIView
from rest_framework.exceptions import NotFound





class CreateRideView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = RideDetailsSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class FindRidesView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = RideSearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rides = serializer.get_available_rides()
        return Response({
            'success': True,
            'data': RideDetailsSerializer(rides, many=True).data
        })

class CreateRideRequestView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, ride_id):
        data = {**request.data, 'ride': ride_id}
        serializer = RideRequestSerializer(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class ListRideRequestsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, ride_id):
        ride = get_object_or_404(RideDetails, id=ride_id, driver=request.user)
        requests = PassengerRideRequest.objects.filter(ride=ride, status='PENDING')
        return Response(RideRequestSerializer(requests, many=True).data)

class ManageRideRequestView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, request_id):
        ride_request = get_object_or_404(PassengerRideRequest, id=request_id)
        serializer = RideActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.perform_action(ride_request, request.user)
        return Response({'success': True, 'data': result})

class RideStatusView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, ride_id):
        ride = get_object_or_404(RideDetails, id=ride_id, driver=request.user)
        serializer = RideStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.update_status(ride)
        return Response({'success': True, 'data': result})

class PassengerStatusView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, request_id):
        ride_request = get_object_or_404(
            PassengerRideRequest,
            id=request_id,
            passenger=request.user
        )
        serializer = PassengerStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.update_status(ride_request)
        return Response({'success': True, 'data': result})
    

class RideHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        

        #  rides where the user is the driver
        driver_rides = RideDetails.objects.filter(driver=user, status__in=['COMPLETED', 'CANCELLED']) 
        
        

        
        #  rides where the user is a passenger
        passenger_rides = RideDetails.objects.filter(
            requests__passenger=user, 
            requests__status__in=['COMPLETED', 'CANCELLED']
        ).distinct()
        
        
        driver_data = RideHistorySerializer(driver_rides, many=True).data
        passenger_data = RideHistorySerializer(passenger_rides, many=True).data
        
        return Response({
            'success': True,
            'data': {
                'as_driver': driver_data,
                'as_passenger': passenger_data
            }
        })






class EmissionsSavingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, ride_id):
        # Check if the user is the driver or a passenger
        ride = None
        
        # Check if the user is the driver
        if request.user.is_authenticated:
            ride = RideDetails.objects.filter(
                id=ride_id,
                driver=request.user
            ).first()
        
       #check if the user is passenger
        if not ride:
            ride = RideDetails.objects.filter(
                id=ride_id,
                requests__passenger=request.user,
                requests__status='CONFIRMED'
            ).first()
        
        if not ride:
            raise NotFound(detail="No matching ride found for the user.")

        
        distance = ride.calculate_distance()
        total_participants = ride.requests.filter(status='CONFIRMED').count() + 1  
        carbon_savings = distance * 411 * (total_participants - 1) / 1000 

        
        emissions_data = {
            'ride_id': ride.id,
            'distance': round(distance, 2),
            'total_participants': total_participants,
            'carbon_savings': round(carbon_savings, 2)
        }

        serializer = EmissionsSavingsSerializer(emissions_data)
        return Response({
            "success": True,
            "data": serializer.data
        })

