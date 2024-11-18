from rest_framework import serializers
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
from .models import RideDetails, PassengerRideRequest

class PointFieldSerializer(serializers.Serializer):
    type = serializers.CharField()
    coordinates = serializers.ListField(
        child=serializers.FloatField(),
        min_length=2,
        max_length=2
    )

    def validate(self, data):
        if data['type'] != 'Point':
            raise serializers.ValidationError("Only Point type is supported")
        return Point(data['coordinates'][0], data['coordinates'][1], srid=4326)

class RideDetailsSerializer(serializers.ModelSerializer):
    driver_name = serializers.SerializerMethodField()
    start_point = PointFieldSerializer()
    end_point = PointFieldSerializer()
    
    class Meta:
        model = RideDetails
        fields = '__all__'
        read_only_fields = ['driver', 'status']

    def get_driver_name(self, obj):
        return obj.driver.get_full_name() or obj.driver.email

    def create(self, validated_data):
        validated_data['driver'] = self.context['request'].user
        return super().create(validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for field in ['start_point', 'end_point']:
            point = getattr(instance, field)
            if point:
                data[field] = {
                    'type': 'Point',
                    'coordinates': [point.x, point.y]
                }
        return {'success': True, 'data': data}

class RideRequestSerializer(serializers.ModelSerializer):
    passenger_name = serializers.SerializerMethodField()
    pickup_point = PointFieldSerializer()
    dropoff_point = PointFieldSerializer()
    
    class Meta:
        model = PassengerRideRequest
        fields = '__all__'
        read_only_fields = ['passenger', 'status']

    def get_passenger_name(self, obj):
        return obj.passenger.get_full_name() or obj.passenger.email

    def validate(self, data):
        ride = data['ride']
        seats = data.get('seats_needed', 1)
        
        if ride.status != 'PENDING':
            raise serializers.ValidationError("This ride is no longer accepting requests")
        
        if seats > ride.available_seats:
            raise serializers.ValidationError(f"Only {ride.available_seats} seats available")
        
        if PassengerRideRequest.objects.filter(
            passenger=self.context['request'].user,
            ride=ride,
            status='PENDING'
        ).exists():
            raise serializers.ValidationError("You already have a pending request for this ride")
            
        return data

    def create(self, validated_data):
        validated_data['passenger'] = self.context['request'].user
        return super().create(validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for field in ['pickup_point', 'dropoff_point']:
            point = getattr(instance, field)
            if point:
                data[field] = {
                    'type': 'Point',
                    'coordinates': [point.x, point.y]
                }
        return {'success': True, 'data': data}
