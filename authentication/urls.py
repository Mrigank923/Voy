from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import RegisterView, CustomTokenObtainPairView,ForgotPasswordView



urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # path('forgot-password/', ForgotPasswordView.as_view(), name='forgot_password'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot_password'),
    
]
