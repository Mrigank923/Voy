import json

from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.models import User

from .models import PassengerRideRequest, RideDetails
from .serializers import (EmissionsSavingsSerializer, PassengerListSerializer,
                          PassengerStatusSerializer, PaymentSerializer,
                          RatingSerializer, RideActionSerializer,
                          RideDetailsSerializer, RideHistorySerializer,
                          RideRequestSerializer, RideSearchSerializer,
                          RideStatusDetailsSerializer, RideStatusSerializer)


class StandardPagination(PageNumberPagination):
    page_size = 10


from rest_framework.exceptions import NotFound


class CreateRideView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user.is_driver_verified:
            return Response(
                {"success": False, "error": "Only verified drivers can create rides"},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = RideDetailsSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class FindRidesView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def post(self, request):
        serializer = RideSearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rides = serializer.get_available_rides()

        paginator = self.pagination_class()
        paginated_rides = paginator.paginate_queryset(rides, request)
        ride_serializer = RideDetailsSerializer(paginated_rides, many=True)

        return Response({"success": True, "data": ride_serializer.data})


class CreateRideRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, ride_id):
        data = {**request.data, "ride": ride_id}
        serializer = RideRequestSerializer(data=data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ListRideRequestsView(APIView):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    def get(self, request, ride_id):
        ride = get_object_or_404(RideDetails, id=ride_id, driver=request.user)
        requests = PassengerRideRequest.objects.filter(ride=ride, status="PENDING")

        # Get paginated data
        paginator = self.pagination_class()
        paginated_requests = paginator.paginate_queryset(requests, request)
        serializer = RideRequestSerializer(paginated_requests, many=True)

        return Response({"success": True, "data": serializer.data})


class ManageRideRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, request_id):
        ride_request = get_object_or_404(PassengerRideRequest, id=request_id)
        serializer = RideActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.perform_action(ride_request, request.user)
        return Response({"success": True, "data": result})


class RideStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, ride_id):
        ride = get_object_or_404(RideDetails, id=ride_id, driver=request.user)
        serializer = RideStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data["status"]
        ride.status = new_status
        ride.save()

        if new_status == "COMPLETED":
            request.user.completed_rides_as_driver += 1
            request.user.save()
            passengers_to_complete = ride.requests.filter(
                status__in=["CONFIRMED", "IN_VEHICLE"]
            )
            for passenger_request in passengers_to_complete:
                passenger_request.passenger.completed_rides_as_passenger += 1
                passenger_request.passenger.save()
            passengers_to_complete.update(status=new_status)
        elif new_status == "CANCELLED":
            ride.requests.filter(status__in=["CONFIRMED", "IN_VEHICLE"]).update(
                status=new_status
            )
        return Response(
            {
                "success": True,
                "data": {"message": f"Ride status updated to {new_status}"},
            }
        )


class PassengerStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, request_id):
        ride_request = get_object_or_404(
            PassengerRideRequest, id=request_id, passenger=request.user
        )
        serializer = PassengerStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.update_status(ride_request)
        return Response({"success": True, "data": result})


class RateDriverView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, ride_id):
        ride = get_object_or_404(
            RideDetails,
            id=ride_id,
            status="COMPLETED",
            requests__passenger=request.user,
            requests__status="COMPLETED",
        )

        # Check if already rated
        if ride.rating_set.filter(from_user=request.user, to_user=ride.driver).exists():
            return Response(
                {"success": False, "error": "You have already rated this driver"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = RatingSerializer(
            data=request.data,
            context={"ride": ride, "from_user": request.user, "to_user": ride.driver},
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({"success": True, "message": "Driver rated successfully"})


class RatePassengerView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, ride_id):
        ride = get_object_or_404(
            RideDetails, id=ride_id, driver=request.user, status="COMPLETED"
        )

        unrated_passengers = (
            User.objects.filter(
                Passenger_ride_requests__ride=ride,
                Passenger_ride_requests__status="COMPLETED",
            )
            .exclude(
                ratings_received__ride=ride, ratings_received__from_user=request.user
            )
            .distinct()
        )

        return Response(
            {
                "success": True,
                "data": PassengerListSerializer(unrated_passengers, many=True).data,
            }
        )

    def post(self, request, ride_id, passenger_id):
        ride = get_object_or_404(
            RideDetails, id=ride_id, driver=request.user, status="COMPLETED"
        )

        passenger = get_object_or_404(
            User,
            id=passenger_id,
            Passenger_ride_requests__ride=ride,
            Passenger_ride_requests__status="COMPLETED",
        )

        if ride.rating_set.filter(from_user=request.user, to_user=passenger).exists():
            return Response(
                {"success": False, "error": "You have already rated this passenger"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = RatingSerializer(
            data=request.data,
            context={"ride": ride, "from_user": request.user, "to_user": passenger},
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({"success": True, "message": "Passenger rated successfully"})


class RideStatusDetailsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, ride_id):
        try:
            ride = (
                RideDetails.objects.filter(id=ride_id)
                .filter(Q(driver=request.user) | Q(requests__passenger=request.user))
                .distinct()
                .get()
            )

            serializer = RideStatusDetailsSerializer(ride)
            return Response({"success": True, "data": serializer.data})

        except RideDetails.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "error": "Ride not found or you don't have permission to view it",
                },
                status=status.HTTP_404_NOT_FOUND,
            )


class CompletePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, request_id):
        ride_request = get_object_or_404(
            PassengerRideRequest, id=request_id, passenger=request.user
        )
        serializer = PaymentSerializer(ride_request, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"success": True, "data": serializer.data})


class RideHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        #  rides where the user is the driver
        driver_rides = RideDetails.objects.filter(
            driver=user, status__in=["COMPLETED", "CANCELLED"]
        )

        #  rides where the user is a passenger
        passenger_rides = RideDetails.objects.filter(
            requests__passenger=user, requests__status__in=["COMPLETED", "CANCELLED"]
        ).distinct()

        driver_data = RideHistorySerializer(driver_rides, many=True).data
        passenger_data = RideHistorySerializer(passenger_rides, many=True).data

        return Response(
            {
                "success": True,
                "data": {"as_driver": driver_data, "as_passenger": passenger_data},
            }
        )


class EmissionsSavingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, ride_id):
        # Check if the user is the driver or a passenger
        ride = None

        # Check if the user is the driver
        if request.user.is_authenticated:
            ride = RideDetails.objects.filter(id=ride_id, driver=request.user).first()

        # check if the user is passenger
        if not ride:
            ride = RideDetails.objects.filter(
                id=ride_id,
                requests__passenger=request.user,
                requests__status="CONFIRMED",
            ).first()

        if not ride:
            raise NotFound(detail="No matching ride found for the user.")

        distance = ride.calculate_distance()
        total_participants = ride.requests.filter(status="CONFIRMED").count() + 1
        carbon_savings = distance * 411 * (total_participants - 1) / 1000

        emissions_data = {
            "ride_id": ride.id,
            "distance": round(distance, 2),
            "total_participants": total_participants,
            "carbon_savings": round(carbon_savings, 2),
        }

        serializer = EmissionsSavingsSerializer(emissions_data)
        return Response({"success": True, "data": serializer.data})
