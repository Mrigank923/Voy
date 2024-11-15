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
)

urlpatterns = [
    path('create/', CreateRideView.as_view(), name='create_ride'),
    path('find/', FindRidesView.as_view(), name='find_rides'),
    path('request/<int:ride_id>/', CreateRideRequestView.as_view(), name='request_ride'),
    path('requests/<int:ride_id>/', ListRideRequestsView.as_view(), name='ride_requests'),
    path('manage-request/<int:request_id>/', ManageRideRequestView.as_view(), name='manage_request'),
]
