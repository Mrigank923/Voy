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
import random
from django.db import transaction
from django.db.utils import IntegrityError
from datetime import timedelta
from django.utils import timezone


# this is just a placeholder view for the deault path
def home_view(request):
    return JsonResponse({"message": "Welcome to the app!"})


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            try:
                
                user = User.objects.create_user(
                    email=serializer.validated_data['email'],
                    password=serializer.validated_data['password'],
                    phone_number=serializer.validated_data['phone_number'],
                    first_name=serializer.validated_data.get('first_name', ''),
                    last_name=serializer.validated_data.get('last_name', '')
                )


                
                # Generate OTPs
                email_otp_instance = OTP.objects.create(
                    user=user,
                    code=''.join([str(random.randint(0, 9)) for _ in range(6)]),
                    type='EMAIL'
                )

                phone_otp_instance = OTP.objects.create(
                    user=user,
                    code=''.join([str(random.randint(0, 9)) for _ in range(6)]),
                    type='PHONE'
                )

                
                # Send email OTP
                send_mail(
                    'Verify Your Email',
                    f'Your email verification code is: {email_otp_instance.code}\n'
                    f'This code will expire in 10 minutes.',
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )


                # Send phone OTP
                api_key = settings.TWOFACTOR_API_KEY
                url = f"https://2factor.in/API/V1/{api_key}/SMS/{user.phone_number}/{phone_otp_instance.code}"
                response = requests.get(url)

                
                if response.json()['Status'] != 'Success':
                    raise Exception("Failed to send phone OTP")

                return Response({
                    'success': True,
                    'message': 'Verification codes sent. Please verify both email and phone.',
                    'user_id': user.id
                }, status=status.HTTP_201_CREATED)


            except Exception as e:
                # If anything fails, cleanup the user
                if 'user' in locals():
                    user.delete()
                return Response({
                    'success': False,
                    'message': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class VerifyRegistrationOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            User.cleanup_expired_registrations()
            
            user = User.objects.get(
                id=request.data.get('user_id'),
                registration_pending=True,
                created_at__gt=timezone.now() - timedelta(minutes=10)
            )

            email_otp = OTP.objects.filter(
                user=user,
                code=request.data.get('email_otp'),
                type='EMAIL',
                is_verified=False
            ).first()
            
            phone_otp = OTP.objects.filter(
                user=user,
                code=request.data.get('phone_otp'),
                type='PHONE',
                is_verified=False
            ).first()

            if not email_otp or not phone_otp or not email_otp.is_valid() or not phone_otp.is_valid():
                return Response({
                    'success': False,
                    'message': 'Invalid or expired OTP codes.'
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                with transaction.atomic():# This will rollback the transaction if any of the queries fail.
                    user.is_active = True
                    user.email_verified = True
                    user.phone_verified = True
                    user.registration_pending = False
                    user.save() 

                    # Mark OTPs as verified
                    email_otp.is_verified = True
                    phone_otp.is_verified = True
                    email_otp.save()
                    phone_otp.save()

            except IntegrityError:# This will catch any duplicate email violations
                return Response({
                    'success': False,
                    'message': 'This email or phone number is already registered.'
                }, status=status.HTTP_400_BAD_REQUEST)

            refresh = RefreshToken.for_user(user)
            
            return Response({
                'success': True,
                'message': 'Registration completed successfully.',
                'user': UserSerializer(user).data,
                'tokens': {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                }
            }, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Invalid or expired registration.'
            }, status=status.HTTP_400_BAD_REQUEST)



class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email'].lower() 
            password = serializer.validated_data['password']
            
            try:
                user = User.objects.get(email=email)
                
                if not user.is_active:
                    return Response({
                        'success': False,
                        'status': 'error',
                        'message': 'Please verify your email and phone number to login.'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                user = authenticate(email=email, password=password)
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
                else:
                    return Response({
                        'success': False,
                        'status': 'error',
                        'message': 'Invalid password'
                    }, status=status.HTTP_400_BAD_REQUEST)
                    
            except User.DoesNotExist:
                return Response({
                    'success': False,
                    'status': 'error',
                    'message': 'No account found with this email'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'success': False,
            'status': 'error',
            'message': 'Invalid input',
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


 
