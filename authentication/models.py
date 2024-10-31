from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
import random
from django.utils import timezone
from datetime import timedelta
import logging
from django.contrib.auth import get_user_model

from django.utils.translation import gettext_lazy as _

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.is_active = False
        user.full_clean()  
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))

        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    username = None 
    email = models.EmailField(unique=True, error_messages={'unique': 'A user with that email already exists.'})
    phone_number = models.CharField(_('phone number'), max_length=15, unique=True)
    first_name = models.CharField(_('first name'), max_length=150)
    last_name = models.CharField(_('last name'), max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'phone_number']

    objects = CustomUserManager()

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        ordering = ['-created_at']

    def __str__(self):
        return self.email

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def clean(self):
        super().clean()
        self.email = self.email.lower()


User = get_user_model()
logger = logging.getLogger(__name__)
#OTP MODEL 
class OTP(models.Model):
    TYPE_CHOICES = (
        ('EMAIL', 'Email'),
        ('PASSOWROD_RESET', 'password_reset'),
        ('PHONE', 'Phone')
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="otp_codes")
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='EMAIL')

    def is_valid(self):
        return (
            timezone.now() <= self.created_at + timedelta(minutes=10) and
            not self.is_verified and
            self.attempts < 3
        )

    @classmethod
    def create_otp_for_user(cls, user, otp_type='EMAIL'):
        
        cls.objects.filter(user=user, is_verified=False, type=otp_type).update(is_verified=True)
        
        otp_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        return cls.objects.create(user=user, code=otp_code, type=otp_type)


