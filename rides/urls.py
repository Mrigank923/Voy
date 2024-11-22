from django.urls import path

from rides.consumers import RideLocationConsumer

from .views import *

urlpatterns = [
    # driver patterns wil the these
    path("driver/create/", CreateRideView.as_view(), name="driver-create-ride"),
    path(
        "driver/<int:ride_id>/status/",
        RideStatusView.as_view(),
        name="driver-update-ride-status",
    ),
    path(
        "driver/requests/<int:ride_id>/",
        ListRideRequestsView.as_view(),
        name="driver-list-requests",
    ),
    path(
        "driver/manage-request/<int:request_id>/",
        ManageRideRequestView.as_view(),
        name="driver-manage-request",
    ),
    # passenger patterns will be these
    path("passenger/search/", FindRidesView.as_view(), name="passenger-search-rides"),
    path(
        "passenger/<int:ride_id>/request/",
        CreateRideRequestView.as_view(),
        name="passenger-request-ride",
    ),
    path(
        "passenger/request/<int:request_id>/status/",
        PassengerStatusView.as_view(),
        name="passenger-update-status",
    ),
    path(
        "passenger/<int:ride_id>/rate-driver/",
        RateDriverView.as_view(),
        name="passenger-rate-driver",
    ),
    path(
        "driver/<int:ride_id>/unrated-passengers/",
        RatePassengerView.as_view(),
        name="driver-unrated-passengers",
    ),
    path(
        "driver/<int:ride_id>/rate-passenger/<int:passenger_id>/",
        RatePassengerView.as_view(),
        name="driver-rate-passenger",
    ),
    path(
        "status/<int:ride_id>/details/",
        RideStatusDetailsView.as_view(),
        name="ride-status-details",
    ),
    path(
        "passenger/request/<int:request_id>/complete-payment/",
        CompletePaymentView.as_view(),
        name="complete-payment",
    ),
    path(
        'ride-history/',
        RideHistoryView.as_view(),
        name='ride-history'
        ),
    path(
        'emissions-savings/<int:ride_id>/',
        EmissionsSavingsView.as_view(),
        name='emissions-savings'
        ),
    
    

    
    
    
    
]

