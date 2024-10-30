from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

from django.contrib.auth import get_user_model
import random
from django.utils import timezone
from datetime import timedelta
import logging

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    username = None 
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email
    

User = get_user_model()
logger = logging.getLogger(__name__)
#OTP MODEL 
class OTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="otp_codes")
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)

    def is_valid(self):
        return (
            timezone.now() <= self.created_at + timedelta(minutes=10) and
            not self.is_verified and
            self.attempts < 3
        )

    @classmethod
    def create_otp_for_user(cls, user):
        
        cls.objects.filter(user=user, is_verified=False).update(is_verified=True)
        
        #Generate otp of 4 digits
        otp_code = ''.join([str(random.randint(0, 9)) for _ in range(4)])
        return cls.objects.create(user=user, code=otp_code)