from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from .models import OTP
from django.db.models import Q
from django.core.validators import RegexValidator


User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = (
            'id', 'email', 'phone_number', 'first_name', 'last_name', 
            'full_name', 'profile_photo', 'gender',
            'emergency_contact_phone','email_verified', 'phone_verified', 'created_at','drivers_license_image', 'is_driver_verified'
        )
        read_only_fields = ('id', 'email', 'email_verified', 'phone_verified', 'created_at', 'is_driver_verified')


    def get_full_name(self, obj):
        return obj.get_full_name()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        validators=[
            RegexValidator(
                regex=r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$',
                message="Password must contain at least 8 characters, one uppercase letter, one lowercase letter, one digit, and one special character."
            )
        ]
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
        extra_kwargs = {
            'email': {
                'required': True,
                'validators': []
            },
            'phone_number': {'required': True}
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({
                "password": "Password fields didn't match."
            })

        attrs['email'] = attrs['email'].lower()
        email = attrs['email']
        phone_number = attrs['phone_number']

        # Check for pending registration
        pending_user = User.objects.filter(
            Q(email=email) | Q(phone_number=phone_number),
            registration_pending=True,
            created_at__gt=timezone.now() - timedelta(minutes=5)
        ).first()

        if pending_user:
            time_remaining = (pending_user.created_at + timedelta(minutes=5) - timezone.now())
            minutes = int(time_remaining.total_seconds() / 60)
            seconds = int(time_remaining.total_seconds() % 60)

            status_message = ""
            next_step = ""

            if not pending_user.email_verified:
                status_message = "Email verification pending"
                next_step = "email_verification"
            else:
                status_message = "Phone verification pending"
                next_step = "phone_verification"

            raise serializers.ValidationError({
                "verification_status": {
                    "user_id": pending_user.id,
                    "message": f"{status_message}. Please verify or wait {minutes}m {seconds}s.",
                    "email_verified": pending_user.email_verified,
                    "phone_verified": pending_user.phone_verified,
                    "next_step": next_step,
                    "expires_in": {
                        "minutes": minutes,
                        "seconds": seconds
                    }
                }
            })

        if User.objects.filter(email=email, registration_pending=False).exists():
            raise serializers.ValidationError({
                "email": "This email is already registered. Please login or use a different email."
            })

        if User.objects.filter(phone_number=phone_number, registration_pending=False).exists():
            raise serializers.ValidationError({
                "phone_number": "This phone number is already registered. Please use a different number."
            })

        return attrs


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(
        required=True,
        error_messages={
            'required': 'Email is required',
            'invalid': 'Please enter a valid email address'
        }
    )
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'},
        error_messages={
            'required': 'Password is required'
        }
    )

    def validate_email(self, value):
        return value.lower()

class VerifyEmailOTPSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    email_otp = serializers.CharField(max_length=6)

    def validate(self, attrs):
        try:
            user = User.objects.get(
                id=attrs['user_id'],
                registration_pending=True,
                is_active=False,
                email_verified=False
            )
        except User.DoesNotExist:
            raise serializers.ValidationError({
                "user_id": "Invalid or already verified user"
            })

        # Get the latest unverified OTP for this user
        otp_instance = OTP.objects.filter(
            user=user,
            code=attrs['email_otp'],
            type='EMAIL',
            is_verified=False
        ).order_by('-created_at').first()

        if not otp_instance:
            raise serializers.ValidationError({
                "email_otp": "Invalid verification code"
            })

        if not otp_instance.is_valid():
            if otp_instance.attempts >= 3:
                raise serializers.ValidationError({
                    "email_otp": "Too many failed attempts. Please request a new code."
                })
            
            otp_instance.attempts += 1
            otp_instance.save()
            raise serializers.ValidationError({
                "email_otp": "Invalid or expired verification code"
            })

        attrs['user'] = user
        attrs['otp_instance'] = otp_instance
        return attrs

    def save(self, **kwargs):
        otp_instance = self.validated_data['otp_instance']
        otp_instance.is_verified = True
        otp_instance.save()
        return self.validated_data['user']

class VerifyPhoneOTPSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    phone_otp = serializers.CharField(max_length=6)

    def validate(self, attrs):
        try:
            user = User.objects.get(
                id=attrs['user_id'],
                registration_pending=True,
                is_active=False,
                email_verified=True,
                phone_verified=False
            )
        except User.DoesNotExist:
            raise serializers.ValidationError({
                "user_id": "Invalid user or wrong verification order"
            })

        otp_instance = OTP.objects.filter(
            user=user,
            code=attrs['phone_otp'],
            type='PHONE',
            is_verified=False
        ).order_by('-created_at').first()

        if not otp_instance:
            raise serializers.ValidationError({
                "phone_otp": "Invalid verification code"
            })

        if not otp_instance.is_valid():
            if otp_instance.attempts >= 3:
                raise serializers.ValidationError({
                    "phone_otp": "Too many failed attempts. Please request a new code."
                })
            
            otp_instance.attempts += 1
            otp_instance.save()
            raise serializers.ValidationError({
                "phone_otp": "Invalid or expired verification code"
            })

        attrs['user'] = user
        attrs['otp_instance'] = otp_instance
        return attrs

    def save(self, **kwargs):
        otp_instance = self.validated_data['otp_instance']
        otp_instance.is_verified = True
        otp_instance.save()
        return self.validated_data['user']

class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(
        error_messages={
            'required': 'Email is required',
            'invalid': 'Please enter a valid email address'
        }
    )

    def validate_email(self, value):
        email = value.lower()
        if not User.objects.filter(email=email, is_active=True).exists():
            raise serializers.ValidationError(
                "No active account found with this email address"
            )
        return email

class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)

    def validate(self, attrs):
        email = attrs['email']
        otp = attrs['otp']

        try:
            user = User.objects.get(email=email)

            # Get the most recent unverified OTP for this user
            otp_instance = OTP.objects.filter(
                user=user,
                is_verified=False  # Ensures we get an unverified OTP
            ).order_by('-created_at').first()

            # Validate the OTP instance exists and matches the provided OTP code
            if not otp_instance or otp_instance.code != otp:
                raise serializers.ValidationError({"otp": "Invalid OTP."})

            # Check if the OTP is still valid
            if not otp_instance.is_valid():
                if otp_instance.attempts >= 3:
                    raise serializers.ValidationError({"otp": "Too many attempts. Please request a new OTP."})
                
                otp_instance.attempts += 1
                otp_instance.save()
                raise serializers.ValidationError({"otp": "Invalid or expired OTP."})

            # Store user and OTP instance in context for later use in save() if needed
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
    
class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        validators=[
            RegexValidator(
                regex=r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$',
                message="Password must contain at least 8 characters, one uppercase letter, one lowercase letter, one digit, and one special character."
            )
        ]
    )
    confirm_password = serializers.CharField(write_only=True, min_length=8)
    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})

        try:
            user = User.objects.get(email=attrs['email'])
            
            # Fetch the most recent verified OTP for this user
            otp_instance = OTP.objects.filter(
                user=user,
                code=attrs['otp'],
                is_verified=True  # Check for only verified OTPs
            ).order_by('-created_at').first()

            if not otp_instance:
                raise serializers.ValidationError({"otp": "Please verify your OTP first."})

            # Check if OTP is still within validity period
            if timezone.now() > otp_instance.created_at + timedelta(minutes=15):
                raise serializers.ValidationError({"otp": "OTP has expired. Please request a new one."})

            self.context['user'] = user
            self.context['otp_instance'] = otp_instance

        except User.DoesNotExist:
            raise serializers.ValidationError({"error": "Invalid credentials."})

        return attrs

    def save(self):
        user = self.context['user']
        user.set_password(self.validated_data['new_password'])
        user.save()

        # Optional: Mark all unverified OTPs as verified to prevent reuse
        OTP.objects.filter(user=user, is_verified=False).update(is_verified=True)

        return user
    


    
    
