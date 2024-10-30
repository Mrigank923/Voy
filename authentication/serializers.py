from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from .models import OTP  
from datetime import timedelta
from django.utils import timezone

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name')

class RegisterSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(write_only=True, required=True)
    last_name = serializers.CharField(write_only=True, required=True)
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('email', 'password', 'confirm_password', 'first_name', 'last_name')

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


#serializer for forgot-password
class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        # Check if the email exists in the database
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email does not exist.")
        return value

#serilaizer for otp 
class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)

    def validate(self, attrs):
        email = attrs['email']
        otp = attrs['otp']
        
        
        try:
            user = User.objects.get(email=email)
            otp_instance = OTP.objects.filter(
                user=user,
                code=otp,
                is_verified=False
            ).order_by('-created_at').first()  

            if not otp_instance:
                raise serializers.ValidationError({"otp": "Invalid OTP."})
            
            if not otp_instance.is_valid():
                if otp_instance.attempts >= 3:
                    raise serializers.ValidationError({"otp": "Too many attempts. Please request a new OTP."})
                
                otp_instance.attempts += 1
                otp_instance.save()
                raise serializers.ValidationError({"otp": "Invalid or expired OTP."})

            self.context['user'] = user
            self.context['otp_instance'] = otp_instance

        except User.DoesNotExist:
            
            raise serializers.ValidationError({"otp": "Invalid OTP."})

        return attrs
    
    def save(self):
        otp_instance = self.context['otp_instance']
        otp_instance.is_verified = True
        otp_instance.save()
        return self.context['user']

#after verification process of reset password
class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, min_length=8)
    #function to check if both the new passwords match or not
    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})

        try:
            user = User.objects.get(email=attrs['email'])
            otp_instance = OTP.objects.filter(
                user=user,
                code=attrs['otp'],
                is_verified=True
            ).order_by('-created_at').first()

            if not otp_instance:
                raise serializers.ValidationError({"otp": "Please verify your OTP first."})

            if timezone.now() > otp_instance.created_at + timedelta(minutes=15):
                raise serializers.ValidationError({"otp": "OTP has expired. Please request a new one."})

            self.context['user'] = user
            self.context['otp_instance'] = otp_instance

        except User.DoesNotExist:
            
            raise serializers.ValidationError({"error": "Invalid credentials."})

        return attrs
    #function that sets the new password as the login password orf user
    def save(self):
        user = self.context['user']
        user.set_password(self.validated_data['new_password'])
        user.save()

       
        OTP.objects.filter(user=user, is_verified=False).update(is_verified=True)
        return user
