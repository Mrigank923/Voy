from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from.views import RegisterView,LoginView,ForgotPasswordView,VerifyOTPView,ResetPasswordView



urlpatterns=[
    path('register/',RegisterView.as_view(),name='register'),
    path('login/',LoginView.as_view(),name='loginr'),
    path('token/refresh/',TokenRefreshView.as_view(),name='token_refresh'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot_password'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify_otp'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset_password'),
   
    
]