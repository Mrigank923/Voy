from rest_framework import serializers
from django.contrib.gis.geos import Point
from .models import RideDetails, PassengerRideRequest

class RideDetailsSerializer(serializers.ModelSerializer):
    driver_name = serializers.CharField(source='driver.username', read_only=True)
    
    class Meta:
        model = RideDetails
        fields = ['id', 'driver_name', 'start_location', 'end_location', 
                 'start_point', 'end_point', 'start_time', 'available_seats', 
                 'status', 'created_at']
        read_only_fields = ['driver', 'status']

    def create(self, validated_data):
        # Convert GeoJSON to Point objects
        if 'start_point' in validated_data and validated_data['start_point']:
            coordinates = validated_data['start_point']['coordinates']
            validated_data['start_point'] = Point(coordinates[0], coordinates[1])
            
        if 'end_point' in validated_data and validated_data['end_point']:
            coordinates = validated_data['end_point']['coordinates']
            validated_data['end_point'] = Point(coordinates[0], coordinates[1])
            
        return super().create(validated_data)

