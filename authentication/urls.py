from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from.views import RegisterView,LoginView,ForgotPasswordView,VerifyOTPView,PasswordResetView



urlpatterns=[
    path('register/',RegisterView.as_view(),name='register'),
    path('login/',LoginView.as_view(),name='loginr'),
    path('token/refresh/',TokenRefreshView.as_view(),name='token_refresh'),
    path('forgotpassword/',ForgotPasswordView.as_view(),name='forgot_password'),
    path('resetpassword/', PasswordResetView.as_view(), name='reset_password'),
    path('verifyotp/', VerifyOTPView.as_view(), name='verify_otp'),
   
    
]