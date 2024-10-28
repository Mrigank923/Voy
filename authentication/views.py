from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.core.mail import send_mail
from django.contrib.auth.models import User

from .serializers import ForgotPasswordRequestSerializer, PasswordResetSerializer
from .models import OTP  






class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'status': 'success',
                'message': 'User registered successfully',
                'user': UserSerializer(user).data,
                'tokens': {
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                }
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
                    'message': 'Login successful',
                    'user': UserSerializer(user).data,
                    'tokens': {
                        'access': str(refresh.access_token),
                        'refresh': str(refresh),
                    }
                })
            return Response({
                'status': 'error',
                'message': 'Invalid credentials'
            }, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUES)




class ForgotPasswordView(APIView):
    #permission_classes = [IsAuthenticated]
    
    def post(self, request):
        
        serializer = ForgotPasswordRequestSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
        
            user = User.objects.get(email=serializer.validated_data['email'])  
            otp_instance = OTP.create_otp_for_user(user)  
            
            send_mail(
                'Password Reset OTP',
                f'Your OTP for password reset is: {otp_instance.code}',
                'voyreply@gmail.com',
                user.email,
            )
            
            return Response({"msg": "OTP sent to your email"}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "OTP has not sent to your email"}, status=status.HTTP_400_BAD_REQUEST)


class VerifyOTPView(APIView):
    #permission_classes = [IsAuthenticated]
    
    def post(self, request):
        email = request.data.get("email")
        otp_code = request.data.get("otp")
        
        try:
            user = User.objects.get(email=email)
            otp_instance = OTP.objects.filter(user=user, code=otp_code).last()
            
            
            if otp_instance and otp_instance.is_valid():
                return Response({"msg": "OTP verified. You can now reset your password."}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "Invalid or expired OTP"}, status=status.HTTP_400_BAD_REQUEST)
                
        except User.DoesNotExist:
            return Response({"error": "User with this email does not exist"}, status=status.HTTP_404_NOT_FOUND)


class PasswordResetView(APIView):
    #permission_classes = [IsAuthenticated]
    
    def post(self, request):
        
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        
        serializer.save()
        
        return Response({"msg": "Password changed successfully"}, status=status.HTTP_200_OK)



    
