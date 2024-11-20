import json

from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.models import User

from .models import PassengerRideRequest, RideDetails
from .serializers import (PassengerListSerializer, PassengerStatusSerializer,
                          PaymentSerializer, RatingSerializer,
                          RideActionSerializer, RideDetailsSerializer,
                          RideRequestSerializer, RideSearchSerializer,
                          RideStatusDetailsSerializer, RideStatusSerializer)


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

    def post(self, request):
        serializer = RideSearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rides = serializer.get_available_rides()
        return Response(
            {"success": True, "data": RideDetailsSerializer(rides, many=True).data}
        )


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

    def get(self, request, ride_id):
        ride = get_object_or_404(RideDetails, id=ride_id, driver=request.user)
        requests = PassengerRideRequest.objects.filter(ride=ride, status="PENDING")
        return Response(RideRequestSerializer(requests, many=True).data)


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

            completed_passengers = ride.requests.filter(status="COMPLETED")
            for passenger_request in completed_passengers:
                passenger_request.passenger.completed_rides_as_passenger += 1
                passenger_request.passenger.save()

        if new_status in ["COMPLETED", "CANCELLED"]:
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
