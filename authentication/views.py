from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny , IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer
from django.http import JsonResponse
from rest_framework_simplejwt.exceptions import TokenError
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.conf import settings
from .serializers import ForgotPasswordSerializer, ResetPasswordSerializer,VerifyOTPSerializer, VerifyRegistrationOTPSerializer, SendPhoneOTPSerializer, VerifyPhoneOTPSerializer 
from .models import OTP  
import logging
from django.contrib.auth import get_user_model
import requests
from django.conf import settings
from django.core.cache import cache
import uuid
import random


# this is just a placeholder view for the deault path
def home_view(request):
    return JsonResponse({"message": "Welcome to the app!"})


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            try:
                
                email = serializer.validated_data['email']
                phone = serializer.validated_data['phone_number']
                password = serializer.validated_data['password']

                temp_user = User.objects.create_unverified_user(
                    email=email,
                    password=password,
                    phone_number=phone,
                    first_name=serializer.validated_data.get('first_name', ''),
                    last_name=serializer.validated_data.get('last_name', '')
                )

                
                # Generate OTPs
                email_otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
                phone_otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
                
                # Store in cache, this will/should be deleted after like 10 minutes
                temp_user_id = str(uuid.uuid4())
                cache_key = f"registration_{temp_user_id}"
                
                cache_data = {
                    'user_dict': {
                        'email': temp_user.email,
                        'password': temp_user.password,  # This is already hashed by set_password
                        'first_name': temp_user.first_name,
                        'last_name': temp_user.last_name,
                        'phone_number': temp_user.phone_number,
                    },
                    'email_otp': email_otp,
                    'phone_otp': phone_otp
                }

                cache.set(cache_key, cache_data, timeout=600)

                # Send email OTP
                send_mail(
                    'Verify Your Email',
                    f'Your email verification code is: {email_otp}\n'
                    f'This code will expire in 10 minutes.',
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )

                # Send phone OTP
                api_key = settings.TWOFACTOR_API_KEY
                url = f"https://2factor.in/API/V1/{api_key}/SMS/{phone}/{phone_otp}"
                response = requests.get(url)
                response_data = response.json()

                if response_data['Status'] != 'Success':
                    raise Exception("Failed to send phone OTP")

                return Response({
                    'success': True,
                    'status': 'success',
                    'message': 'Verification codes sent. Please verify both email and phone.',
                    'temp_user_id': temp_user_id
                }, status=status.HTTP_201_CREATED)

            except Exception as e:
                if 'cache_key' in locals():
                    cache.delete(cache_key)
                return Response({
                    'success': False,
                    'status': 'error',
                    'message': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            'success': False,
            'status': 'error',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)



    

class VerifyRegistrationOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyRegistrationOTPSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                cached_data = serializer.context['cached_data']
                cache_key = serializer.context['cache_key']
                
                # Create and save the verified user
                user_data = cached_data['user_dict']
                user = User.objects.create(
                    email=user_data['email'],
                    password=user_data['password'],
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name'],
                    phone_number=user_data['phone_number'],
                    is_active=True,
                    email_verified=True,
                    phone_verified=True,
                    registration_pending=False
                )
                
                # Clean up cache
                cache.delete(cache_key)
                
                # Generate tokens
                refresh = RefreshToken.for_user(user)
                
                return Response({
                    'success': True,
                    'status': 'success',
                    'message': 'Registration completed successfully.',
                    'user': UserSerializer(user).data,
                    'tokens': {
                        'access': str(refresh.access_token),
                        'refresh': str(refresh),
                    }
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                return Response({
                    'success': False,
                    'status': 'error',
                    'message': str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
                
        return Response({
            'success': False,
            'status': 'error',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)



class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = authenticate(
                email=serializer.validated_data['email'],
                password=serializer.validated_data['password']
            )
            if user:
                refresh = RefreshToken.for_user(user)
                return Response({
                    'status': 'success',
                    'success': True,
                    'message': 'Login successful',
                    'user': UserSerializer(user).data,
                    'tokens': {
                        'access': str(refresh.access_token),
                        'refresh': str(refresh),
                    }
                })
            return Response({
            'success': False,
            'status': 'error',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
        
User = get_user_model()
logger = logging.getLogger(__name__)


class ForgotPasswordView(APIView):
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)

        if serializer.is_valid():
            email = serializer.validated_data['email']
            user = User.objects.get(email=email)  

            
            otp_instance = OTP.create_otp_for_user(user)

            
            try:
                send_mail(
                    'Password Reset OTP',
                    f'Your OTP for password reset is: {otp_instance.code}\n'
                    f'This code will expire in 10 minutes.',
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )
                return Response(
                    {'success': True,
                     "message": "An OTP has been sent to the registered email."},
                    status=status.HTTP_200_OK
                )
            except Exception as e:
                
                logger.error(f"Failed to send password reset OTP to {email}: {str(e)}")
                return Response(
                    {'success': False,
                     "message": "Failed to send OTP. Please try again later."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class VerifyOTPView(APIView):
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(
                {'success': True,
                 "message": "OTP verified successfully. You can now reset your password."},
                status=status.HTTP_200_OK
            )
        return Response({
            'success': False,
            'status': 'error',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class ResetPasswordView(APIView):
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(
                {'success': True,
                 "message": "Password reset successful"},
                status=status.HTTP_200_OK
            )
        return Response({
            'success': False,
            'status': 'error',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    
class UserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class CustomTokenRefreshView(APIView):
    print(9);
    permission_classes = [AllowAny]
    
    def post(self, request):
        print(1);
        try:
            refresh_token = request.data.get('refresh')
            print(2);
            if not refresh_token:
                return Response({
                    'error': 'Refresh token is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            print(3);
            # Verify and create new tokens
            refresh = RefreshToken(refresh_token)
            print(4);
            
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh)
            }, status=status.HTTP_200_OK)

        except TokenError as e:
            print(5);
            return Response({
                'error': 'Invalid or expired refresh token'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        except Exception as e:
            print(7);
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        print(8);
        return Response({
            'string': 'hi there'
        })


class RefreshViewNew(APIView):

    permission_classes = [AllowAny]
    
    def post(self, request):
        # print(1);
        try:
            refresh_token = request.data.get('refresh')
            # print(2);
            if not refresh_token:
                return Response({
                    'error': 'Refresh token is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            # print(3);
            # Verify and create new tokens
            refresh = RefreshToken(refresh_token)
            # print(4);
            
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh)
            }, status=status.HTTP_200_OK)

        except TokenError as e:
            # print(5);
            return Response({
                'error': 'Invalid or expired refresh token'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        except Exception as e:
            # print(7);
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        

class SendPhoneOTPView(APIView):
    permission_classes = [AllowAny]  

    def post(self, request):
        serializer = SendPhoneOTPSerializer(data=request.data)
        if serializer.is_valid():
            phone_number = serializer.validated_data['phone_number']
            user = User.objects.get(phone_number=phone_number)

            otp_instance = OTP.create_otp_for_user(user, otp_type='PHONE')

            try:
                api_key = settings.TWOFACTOR_API_KEY
                url = f"https://2factor.in/API/V1/{api_key}/SMS/{phone_number}/{otp_instance.code}"
                
                response = requests.get(url)
                response_data = response.json()

                if response_data['Status'] == 'Success':
                    return Response({
                        'success': True,
                        'status': 'success',
                        'message': 'OTP sent successfully to your phone number.'
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        'success': False,
                        'status': 'error',
                        'message': 'Failed to send OTP. Please try again.'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            except Exception as e:
                logger.error(f"Failed to send phone OTP to {phone_number}: {str(e)}")
                return Response({
                    'success': False,
                    'status': 'error',
                    'message': 'Failed to send OTP. Please try again later.'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            'success': False,
            'status': 'error',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class VerifyPhoneOTPView(APIView):
    permission_classes = [AllowAny] 
    def post(self, request):
        serializer = VerifyPhoneOTPSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                'success': True,
                'status': 'success',
                'message': 'Phone number verified successfully'
            }, status=status.HTTP_200_OK)
        return Response({
            'success': False,
            'status': 'error',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


 
