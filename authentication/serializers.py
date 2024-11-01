from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import OTP  
from datetime import timedelta
from django.utils import timezone
from django.core.cache import cache



User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'full_name', 'created_at')
        read_only_fields = ('id', 'created_at')

    def get_full_name(self, obj):
        return obj.get_full_name()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        validators=[validate_password]
    )
    confirm_password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    first_name = serializers.CharField(required=False, allow_blank=True)  
    last_name = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ('email', 'password', 'confirm_password', 'phone_number', 'first_name', 'last_name')

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def validate_email(self, value):
        email = value.lower()
        if User.objects.filter(email=email, registration_pending=False).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return email

    def validate_phone_number(self, value):
        if User.objects.filter(phone_number=value, registration_pending=False).exists():
            raise serializers.ValidationError("A user with this phone number already exists.")
        return value



class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate_email(self, value):
        """
        Normalize email for login.
        """
        return value.lower()

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email does not exist.")
        return value

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


class VerifyRegistrationOTPSerializer(serializers.Serializer):
    temp_user_id = serializers.CharField()
    email_otp = serializers.CharField(max_length=6)
    phone_otp = serializers.CharField(max_length=6)

    def validate(self, attrs):
        temp_user_id = attrs['temp_user_id']
        email_otp = attrs['email_otp']
        phone_otp = attrs['phone_otp']
        
        cache_key = f"registration_{temp_user_id}"
        cached_data = cache.get(cache_key)
        
        if not cached_data:
            raise serializers.ValidationError({
                "error": "Registration session expired. Please register again."
            })
            
        if email_otp != cached_data['email_otp']:
            raise serializers.ValidationError({
                "email_otp": "Invalid email verification code."
            })
            
        if phone_otp != cached_data['phone_otp']:
            raise serializers.ValidationError({
                "phone_otp": "Invalid phone verification code."
            })
            
        self.context['cached_data'] = cached_data
        self.context['cache_key'] = cache_key
        return attrs

    
    def save(self):
        user = self.context['user']
        otp_instance = self.context['otp_instance']
        
        otp_instance.is_verified = True
        otp_instance.save()
        
        user.email_verified = True
        user.is_active = True 
        user.save()
        
        return user



class SendPhoneOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15, required=True)

    def validate_phone_number(self, value):
        if not User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("User with this phone number does not exist.")
        return value

class VerifyPhoneOTPSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15, required=True)
    phone_otp = serializers.CharField(max_length=6, required=True)

    def validate(self, attrs):
        phone_number = attrs['phone_number']
        phone_otp = attrs['phone_otp']
        
        try:
            user = User.objects.get(phone_number=phone_number)
            otp_instance = OTP.objects.filter(
                user=user,
                code=phone_otp,
                type='PHONE',
                is_verified=False
            ).order_by('-created_at').first()

            if not otp_instance:
                raise serializers.ValidationError({"phone_otp": "Invalid OTP."})
            
            if not otp_instance.is_valid():
                if otp_instance.attempts >= 3:
                    raise serializers.ValidationError({"phone_otp": "Too many attempts. Please request a new OTP."})
                
                otp_instance.attempts += 1
                otp_instance.save()
                raise serializers.ValidationError({"phone_otp": "Invalid or expired OTP."})

            self.context['user'] = user
            self.context['otp_instance'] = otp_instance

        except User.DoesNotExist:
            raise serializers.ValidationError({"phone_otp": "Invalid phone number."})

        return attrs
    
    def save(self):
        user = self.context['user']
        otp_instance = self.context['otp_instance']
        
        otp_instance.is_verified = True
        otp_instance.save()
        
        user.phone_verified = True
        user.save()
        
        return user
