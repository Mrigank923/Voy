from django.urls import path
from .views import RegisterView, LoginView, UserView, CustomTokenRefreshView, RefreshViewNew
from rest_framework_simplejwt.views import TokenRefreshView
from.views import RegisterView,LoginView,ForgotPasswordView,VerifyOTPView,ResetPasswordView, VerifyRegistrationOTPView, SendPhoneOTPView, VerifyPhoneOTPView



urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('refresh/', RefreshViewNew.as_view() , name='refresh'),
    path('user/', UserView.as_view(), name='user'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot_password'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify_otp'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset_password'),
    path('verify-registration/', VerifyRegistrationOTPView.as_view(), name='verify_registration'),
    path('send-phone-otp/', SendPhoneOTPView.as_view(), name='send_phone_otp'),
    path('verify-phone-otp/', VerifyPhoneOTPView.as_view(), name='verify_phone_otp')
]

