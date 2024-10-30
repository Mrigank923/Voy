from django.urls import path
from .views import RegisterView, LoginView, UserView, CustomTokenRefreshView, RefreshViewNew

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('refresh/', RefreshViewNew.as_view() , name='refresh'),
    path('user/', UserView.as_view(), name='user'),
]
