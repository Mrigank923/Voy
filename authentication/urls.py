from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from.views import RegisterView,LoginView,UserChangePasswordView,ForgotPasswordView


urlpatterns=[
    path('register/',RegisterView.as_view(),name='register'),
    path('login/',LoginView.as_view(),name='loginr'),
    path('token/refresh/',TokenRefreshView.as_view(),name='token_refresh'),
    path('changepassword/',UserChangePasswordView.as_view(),name='change_password'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot_password'),
]