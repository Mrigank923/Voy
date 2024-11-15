from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
from .models import RideDetails, PassengerRideRequest
from .serializers import RideDetailsSerializer
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

