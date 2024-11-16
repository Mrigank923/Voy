from rest_framework import serializers
from django.contrib.gis.geos import Point
from .models import RideDetails, PassengerRideRequest

class RideDetailsSerializer(serializers.ModelSerializer):
    driver_name = serializers.CharField(source='driver.username', read_only=True)
    start_point = serializers.JSONField()
    end_point = serializers.JSONField()
    
    class Meta:
        model = RideDetails
        fields = ['id', 'driver_name', 'start_location', 'end_location', 
                 'start_point', 'end_point', 'start_time', 'available_seats', 
                 'status', 'created_at']
        read_only_fields = ['driver', 'status']

    def validate_start_point(self, value):
        try:
            if not isinstance(value, dict) or 'type' not in value or value['type'] != 'Point':
                raise serializers.ValidationError("Invalid GeoJSON Point format")
            return Point(value['coordinates'][0], value['coordinates'][1], srid=4326)
        except (KeyError, IndexError, TypeError):
            raise serializers.ValidationError("Invalid coordinates format")

    def validate_end_point(self, value):
        try:
            if not isinstance(value, dict) or 'type' not in value or value['type'] != 'Point':
                raise serializers.ValidationError("Invalid GeoJSON Point format")
            return Point(value['coordinates'][0], value['coordinates'][1], srid=4326)
        except (KeyError, IndexError, TypeError):
            raise serializers.ValidationError("Invalid coordinates format")

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # Convert Point objects back to GeoJSON
        ret['start_point'] = {
            'type': 'Point',
            'coordinates': [instance.start_point.x, instance.start_point.y]
        }
        ret['end_point'] = {
            'type': 'Point',
            'coordinates': [instance.end_point.x, instance.end_point.y]
        }
        return ret

class PassengerRideRequestSerializer(serializers.ModelSerializer):
    passenger_name = serializers.CharField(source='passenger.username', read_only=True)
    pickup_point = serializers.JSONField(required=True)
    dropoff_point = serializers.JSONField(required=True)
    
    class Meta:
        model = PassengerRideRequest
        fields = ['id', 'passenger_name', 'ride', 'pickup_location', 'dropoff_location',
                 'pickup_point', 'dropoff_point', 'seats_needed', 'status', 'created_at']
        read_only_fields = ['passenger', 'status']

    def validate_pickup_point(self, value):
        try:
            if not isinstance(value, dict) or 'type' not in value or value['type'] != 'Point':
                raise serializers.ValidationError("Invalid GeoJSON Point format")
            return Point(value['coordinates'][0], value['coordinates'][1], srid=4326)
        except (KeyError, IndexError, TypeError):
            raise serializers.ValidationError("Invalid coordinates format")

    def validate_pickup_point(self, value):
        try:
            if not isinstance(value, dict) or 'type' not in value or value['type'] != 'Point':
                raise serializers.ValidationError("Invalid GeoJSON Point format")
            return Point(value['coordinates'][0], value['coordinates'][1], srid=4326)
        except (KeyError, IndexError, TypeError):
            raise serializers.ValidationError("Invalid coordinates format")

    def validate_dropoff_point(self, value):
        try:
            if not isinstance(value, dict) or 'type' not in value or value['type'] != 'Point':
                raise serializers.ValidationError("Invalid GeoJSON Point format")
            return Point(value['coordinates'][0], value['coordinates'][1], srid=4326)
        except (KeyError, IndexError, TypeError):
            raise serializers.ValidationError("Invalid coordinates format")

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if instance.pickup_point:
            ret['pickup_point'] = {
                'type': 'Point',
                'coordinates': [instance.pickup_point.x, instance.pickup_point.y]
            }
        if instance.dropoff_point:
            ret['dropoff_point'] = {
                'type': 'Point',
                'coordinates': [instance.dropoff_point.x, instance.dropoff_point.y]
            }
        return ret
