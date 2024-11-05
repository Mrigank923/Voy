from django.urls import path
from .views import RegisterView, LoginView, UserView, RefreshViewNew
from.views import RegisterView,LoginView,ForgotPasswordView,VerifyOTPView,ResetPasswordView, VerifyPhoneOTPView, VerifyEmailOTPView



urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('verify-email/', VerifyEmailOTPView.as_view(), name='verify_email'),
    path('verify-phone/', VerifyPhoneOTPView.as_view(), name='verify_phone'),
    path('login/', LoginView.as_view(), name='login'),
    path('refresh/', RefreshViewNew.as_view(), name='refresh'),
    path('user/', UserView.as_view(), name='user'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot_password'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify_otp'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset_password'),

]

