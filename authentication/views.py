from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth import authenticate, get_user_model
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
import logging
import requests
from django.http import JsonResponse
import random
from django.db.models import Q
import cloudinary.uploader


from .serializers import (
    RegisterSerializer, 
    LoginSerializer, 
    UserSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
    VerifyOTPSerializer,
    VerifyEmailOTPSerializer,
    VerifyPhoneOTPSerializer
)
from .models import OTP, User

logger = logging.getLogger(__name__)

def home_view(request):
    return JsonResponse({"message": "Welcome to the app!"})

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            serializer = RegisterSerializer(data=request.data)
            if not serializer.is_valid():
                if 'verification_status' in serializer.errors:
                    return Response({
                        'success': False,
                        'message': 'Registration already in progress',
                        'registration_status': serializer.errors['verification_status']
                    }, status=status.HTTP_409_CONFLICT)
                
                return Response({
                    'success': False,
                    'message': 'Validation failed',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            email = serializer.validated_data['email']
            phone_number = serializer.validated_data['phone_number']

            # Clean up expired registrations
            User.cleanup_expired_registrations(email=email, phone_number=phone_number)

            # Delete any existing pending registrations for this email/phone
            User.objects.filter(
                Q(email=email) | Q(phone_number=phone_number),
                registration_pending=True
            ).delete()

            # Create new user and send OTP
            with transaction.atomic():
                user = User.objects.create_user(
                    email=email,
                    password=serializer.validated_data['password'],
                    phone_number=phone_number,
                    first_name=serializer.validated_data.get('first_name', ''),
                    last_name=serializer.validated_data.get('last_name', ''),
                    is_active=False,
                    email_verified=False,
                    phone_verified=False,
                    registration_pending=True
                )

                email_otp = OTP.create_otp_for_user(user, 'EMAIL')
                
                try:
                    send_mail(
                        'Verify Your Email',
                        f'Your email verification code is: {email_otp.code}\n'
                        f'This code will expire in 5 minutes.',
                        settings.DEFAULT_FROM_EMAIL,
                        [email],
                        fail_silently=False,
                    )
                except Exception as e:
                    logger.error(f"Failed to send email OTP: {str(e)}")
                    raise Exception("Failed to send verification email. Please try again.")

                return Response({
                    'success': True,
                    'message': 'Registration initiated. Please verify your email.',
                    'registration_status': {
                        'user_id': user.id,
                        'email': user.email,
                        'phone_number': user.phone_number,
                        'verification_status': {
                            'email_verified': False,
                            'phone_verified': False
                        },
                        'next_step': 'email_verification',
                        'expires_in': {
                            'minutes': 5,
                            'seconds': 0
                        }
                    }
                }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class VerifyEmailOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            serializer = VerifyEmailOTPSerializer(data=request.data)
            if not serializer.is_valid():
                return Response({
                    'success': False,
                    'message': 'Validation failed',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            user = serializer.validated_data['user']
            
            with transaction.atomic():
                user.email_verified = True
                user.save()

                # Generate and send phone OTP
                phone_otp = OTP.create_otp_for_user(user, 'PHONE')
                
                try:
                    api_key = settings.TWOFACTOR_API_KEY
                    url = f"https://2factor.in/API/V1/{api_key}/SMS/{user.phone_number}/{phone_otp.code}"
                    response = requests.get(url)

                    if response.json()['Status'] != 'Success':
                        raise Exception("Failed to send phone verification code")

                except Exception as e:
                    logger.error(f"Failed to send phone OTP: {str(e)}")
                    raise Exception("Failed to send phone verification code. Please try again.")

            return Response({
                'success': True,
                'message': 'Email verified successfully. Please verify your phone number.',
                'user_id': user.id
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class VerifyPhoneOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            serializer = VerifyPhoneOTPSerializer(data=request.data)
            if not serializer.is_valid():
                return Response({
                    'success': False,
                    'message': 'Validation failed',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            user = serializer.validated_data['user']
            
            if not user.email_verified:
                return Response({
                    'success': False,
                    'message': 'Please verify your email first'
                }, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                user.phone_verified = True
                user.is_active = True
                user.registration_pending = False
                user.save()

                # Generate tokens
                refresh = RefreshToken.for_user(user)
                
                return Response({
                    'success': True,
                    'message': 'Phone verified successfully. Registration complete.',
                    'user': UserSerializer(user).data,
                    'tokens': {
                        'access': str(refresh.access_token),
                        'refresh': str(refresh),
                    }
                }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            serializer = LoginSerializer(data=request.data)
            if not serializer.is_valid():
                return Response({
                    'success': False,
                    'message': 'Validation failed',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            email = serializer.validated_data['email'].lower()
            password = serializer.validated_data['password']
            
            try:
                user = User.objects.get(email=email)
                
                if not user.is_active:
                    registration_status = []
                    if not user.email_verified:
                        registration_status.append("email verification")
                    if not user.phone_verified:
                        registration_status.append("phone verification")
                    
                    pending_steps = " and ".join(registration_status)
                    return Response({
                        'success': False,
                        'message': f'Please complete {pending_steps} to login.',
                        'pending_verification': registration_status
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                user = authenticate(email=email, password=password)
                if user:
                    refresh = RefreshToken.for_user(user)
                    return Response({
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
                        'message': 'Invalid password'
                    }, status=status.HTTP_400_BAD_REQUEST)
                    
            except User.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'No account found with this email'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return Response({
                'success': False,
                'message': 'An error occurred during login'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            serializer = ForgotPasswordSerializer(data=request.data)
            if not serializer.is_valid():
                return Response({
                    'success': False,
                    'message': 'Validation failed',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            email = serializer.validated_data['email']
            user = User.objects.get(email=email)

            otp_instance = OTP.create_otp_for_user(user, otp_type='PASSWORD_RESET')

            try:
                send_mail(
                    'Password Reset OTP',
                    f'Your OTP for password reset is: {otp_instance.code}\n'
                    f'This code will expire in 5 minutes.',
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )
                return Response({
                    'success': True,
                    'message': 'Password reset OTP has been sent to your email.'
                }, status=status.HTTP_200_OK)
            except Exception as e:
                logger.error(f"Failed to send password reset OTP: {str(e)}")
                return Response({
                    'success': False,
                    'message': 'Failed to send OTP. Please try again later.'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except User.DoesNotExist:
            return Response({
                'success': False,
                'message': 'No account found with this email'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Forgot password error: {str(e)}")
            return Response({
                'success': False,
                'message': 'An error occurred while processing your request'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            serializer = VerifyOTPSerializer(data=request.data)
            if not serializer.is_valid():
                return Response({
                    'success': False,
                    'message': 'Validation failed',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            user = serializer.save()
            return Response({
                'success': True,
                'message': 'OTP verified successfully. You can now reset your password.'
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"OTP verification error: {str(e)}")
            return Response({
                'success': False,
                'message': 'An error occurred while verifying OTP'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            serializer = ResetPasswordSerializer(data=request.data)
            if not serializer.is_valid():
                return Response({
                    'success': False,
                    'message': 'Validation failed',
                    'errors': serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)

            user = serializer.save()
            return Response({
                'success': True,
                'message': 'Password reset successful'
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Password reset error: {str(e)}")
            return Response({
                'success': False,
                'message': 'An error occurred while resetting password'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            serializer = UserSerializer(request.user)
            return Response({
                'success': True,
                'user': serializer.data
            })
        except Exception as e:
            logger.error(f"User view error: {str(e)}")
            return Response({
                'success': False,
                'message': 'An error occurred while fetching user data'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def put(self, request):
        try:
            # Handle profile photo upload
            profile_photo = request.FILES.get('profile_photo')
            if profile_photo:
                try:
                    # Upload to cloudinary
                    upload_result = cloudinary.uploader.upload(
                        profile_photo,
                        folder='profile_photos/',
                        allowed_formats=['jpg', 'png', 'jpeg'],
                        max_file_size=9000000  
                    )
                    request.data['profile_photo'] = upload_result['public_id']
                except Exception as e:
                    logger.error(f"Cloudinary upload error: {str(e)}")
                    return Response({
                        'success': False,
                        'message': 'Failed to upload profile photo'
                    }, status=status.HTTP_400_BAD_REQUEST)

            serializer = UserSerializer(
                request.user,
                data=request.data,
                partial=True
            )
            
            if serializer.is_valid():
                if profile_photo and request.user.profile_photo:
                    try:
                        cloudinary.uploader.destroy(request.user.profile_photo.public_id)
                    except Exception as e:
                        logger.warning(f"Failed to delete old profile photo: {str(e)}")

                serializer.save()
                return Response({
                    'success': True,
                    'message': 'Profile updated successfully',
                    'user': serializer.data
                })
            
            return Response({
                'success': False,
                'message': 'Validation failed',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Profile update error: {str(e)}")
            return Response({
                'success': False,
                'message': 'Failed to update profile'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RefreshViewNew(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if not refresh_token:
                return Response({
                    'success': False,
                    'message': 'Refresh token is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            refresh = RefreshToken(refresh_token)
            return Response({
                'success': True,
                'tokens': {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh)
                }
            }, status=status.HTTP_200_OK)

        except TokenError:
            return Response({
                'success': False,
                'message': 'Invalid or expired refresh token'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        except Exception as e:
            logger.error(f"Token refresh error: {str(e)}")
            return Response({
                'success': False,
                'message': 'An error occurred while refreshing token'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class ResendOTPView(APIView):
    def post(self, request):
        email = request.data.get('email')

        try:
            user = User.objects.get(email=email)
            
            # Check if an OTP exists and when it was last sent
            otp_instance = OTP.objects.filter(user=user).order_by('-created_at').first()
            if otp_instance:
                time_since_last_otp = timezone.now() - otp_instance.created_at
                if time_since_last_otp < timedelta(seconds=30):
                    return Response(
                        {"success": False, "message": "Please wait 30 seconds before requesting a new OTP."},
                        status=status.HTTP_429_TOO_MANY_REQUESTS
                    )
            
            # Create a new OTP for the user
            new_otp = OTP.create_otp_for_user(user)
            
            # Send the new OTP via email
            send_mail(
                'Resend Password Reset OTP',
                f'Your new OTP for password reset is: {new_otp.code}\n'
                f'This code will expire in 10 minutes.',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            return Response(
                {'success': True, "message": "A new OTP has been sent to the registered email."},
                status=status.HTTP_200_OK
            )
        
        except User.DoesNotExist:
            return Response(
                {"success": False, "message": "User with this email does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Failed to resend OTP to {email}: {str(e)}")
            return Response(
                {"success": False, "message": "Failed to resend OTP. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ResendEmailOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            email = request.data.get('email')
            if not email:
                return Response({
                    'success': False,
                    'message': 'Email is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            user = User.objects.filter(email=email).first()
            if not user:
                return Response({
                    'success': False,
                    'message': 'User with this email does not exist'
                }, status=status.HTTP_404_NOT_FOUND)

            # Create and send a new OTP for email verification
            email_otp = OTP.create_otp_for_user(user, 'EMAIL')
            send_mail(
                'Email Verification OTP',
                f'Your OTP for email verification is: {email_otp.code}\nThis code will expire in 10 minutes.',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )

            return Response({
                'success': True,
                'message': 'A new OTP has been sent to your email address.'
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Failed to resend email OTP: {str(e)}")
            return Response({
                'success': False,
                'message': 'Failed to resend OTP. Please try again later.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class ResendPhoneOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            phone_number = request.data.get('phone_number')
            if not phone_number:
                return Response({
                    'success': False,
                    'message': 'Phone number is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            user = User.objects.filter(phone_number=phone_number).first()
            if not user:
                return Response({
                    'success': False,
                    'message': 'User with this phone number does not exist'
                }, status=status.HTTP_404_NOT_FOUND)

            # Create and send a new OTP for phone verification
            phone_otp = OTP.create_otp_for_user(user, 'PHONE')
            
            api_key = settings.TWOFACTOR_API_KEY
            url = f"https://2factor.in/API/V1/{api_key}/SMS/{phone_number}/{phone_otp.code}"
            response = requests.get(url)

            if response.json()['Status'] != 'Success':
                raise Exception("Failed to send phone verification code")

            return Response({
                'success': True,
                'message': 'A new OTP has been sent to your phone number.'
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Failed to resend phone OTP: {str(e)}")
            return Response({
                'success': False,
                'message': 'Failed to resend OTP. Please try again later.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

