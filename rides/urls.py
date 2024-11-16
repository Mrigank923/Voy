# API For drivers to create rides
# API For passengers to find rides
# API For passengers to request rides
# API For drivers to manage requests
# API For updating ride location
# API For completing rides
# API For post-ride ratings

from django.urls import path
from .views import (
    CreateRideView, 
    FindRidesView,
    CreateRideRequestView,
    ManageRideRequestView,
    ListRideRequestsView,
    RideStatusView,
    PassengerStatusView
)

urlpatterns = [
    #driver patterns wil the these
    path('driver/create/', CreateRideView.as_view(), name='driver-create-ride'),
    path('driver/<int:ride_id>/status/', RideStatusView.as_view(), name='driver-update-ride-status'),
    path('driver/requests/<int:ride_id>/', ListRideRequestsView.as_view(), name='driver-list-requests'),
    path('driver/manage-request/<int:request_id>/', ManageRideRequestView.as_view(), name='driver-manage-request'),
    #passenger patterns will be these
    path('passenger/available/', FindRidesView.as_view(), name='passenger-find-rides'),
    path('passenger/<int:ride_id>/request/', CreateRideRequestView.as_view(), name='passenger-request-ride'),
    path('passenger/request/<int:request_id>/status/', PassengerStatusView.as_view(), name='passenger-update-status'),

]
