import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import IntegrityError, models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class CustomUserManager(BaseUserManager):

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")

        email = self.normalize_email(email)

        self.model.cleanup_expired_registrations(email=email)

        pending_user = self.model.objects.filter(
            email=email,
            registration_pending=True,
            created_at__gt=timezone.now() - timedelta(minutes=5),
        ).first()

        if pending_user:
            time_remaining = (
                pending_user.created_at + timedelta(minutes=5) - timezone.now()
            )
            minutes = int(time_remaining.total_seconds() / 60)
            seconds = int(time_remaining.total_seconds() % 60)

            if not pending_user.email_verified:
                raise ValueError(
                    f"Email verification pending. Please verify or wait {minutes}m {seconds}s."
                )
            else:
                raise ValueError(
                    f"Phone verification pending. Please verify or wait {minutes}m {seconds}s."
                )

        extra_fields.setdefault("registration_pending", True)
        extra_fields.setdefault("is_active", False)
        user = self.model(email=email, **extra_fields)

        if password:
            user.set_password(password)

        try:
            user.full_clean()
            user.save(using=self._db)
        except IntegrityError:
            raise ValueError("An account with this email already exists.")

        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    phone_number = models.CharField(_("phone number"), max_length=15)
    first_name = models.CharField(_("first name"), max_length=150, blank=True)
    last_name = models.CharField(_("last name"), max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    registration_pending = models.BooleanField(default=True)
    profile_photo = models.ImageField(upload_to='profile_photos/', null=True, blank=True)
    gender = models.CharField(
        max_length=10,
        choices=[("MALE", "Male"), ("FEMALE", "Female"), ("OTHER", "Other")],
        blank=True,
        null=True,
    )
    emergency_contact_phone = models.CharField(max_length=15, blank=True, null=True)
    drivers_license_image = models.ImageField(upload_to='drivers_licenses/', null=True, blank=True)
    is_driver_verified = models.BooleanField(default=False)
    is_driver = models.BooleanField(default=False)
    current_role = models.CharField(
        max_length=10,
        choices=[("DRIVER", "Driver"), ("PASSENGER", "Passenger")],
        default="PASSENGER",
    )
    rating_as_driver = models.FloatField(default=0.0)
    rating_as_passenger = models.FloatField(default=0.0)
    vehicle_number = models.CharField(max_length=20, blank=True, null=True)
    vehicle_model = models.CharField(max_length=50, blank=True, null=True)
    completed_rides_as_driver = models.IntegerField(default=0)
    completed_rides_as_passenger = models.IntegerField(default=0)
    total_seats = models.IntegerField(default=0)


    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["phone_number"]

    objects = CustomUserManager()

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["email"],
                condition=models.Q(registration_pending=False),
                name="unique_verified_email",
            ),
            models.UniqueConstraint(
                fields=["phone_number"],
                condition=models.Q(registration_pending=False),
                name="unique_verified_phone",
            ),
        ]
    

    @classmethod
    def cleanup_expired_registrations(cls, email=None, phone_number=None):
        expired_time = timezone.now() - timedelta(minutes=5)

        base_query = Q(registration_pending=True, created_at__lt=expired_time)

        if email or phone_number:
            specific_query = Q()
            if email:
                specific_query |= Q(email=email, registration_pending=True)
            if phone_number:
                specific_query |= Q(
                    phone_number=phone_number, registration_pending=True
                )

            final_query = base_query | specific_query
        else:
            final_query = base_query

        deleted_count = cls.objects.filter(final_query).delete()[0]
        return deleted_count

    def save(self, *args, **kwargs):
        if self.drivers_license_image:
            self.is_driver_verified = True
        else:
            self.is_driver_verified = False

        if self._state.adding and self.registration_pending:
            User.objects.filter(
                Q(email=self.email) | Q(phone_number=self.phone_number),
                registration_pending=True,
                created_at__lt=timezone.now() - timedelta(minutes=5),
            ).delete()
        super().save(*args, **kwargs)

    @property
    def registration_expired(self):
        if self.registration_pending:
            return self.created_at < timezone.now() - timedelta(minutes=5)
        return False

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    def __str__(self):
        full_name = self.get_full_name()
        if full_name:
            return f"{full_name} ({self.email}) - {self.current_role}"
        return f"{self.email} - {self.current_role}"

    def update_rating(self, new_rating, as_driver=True):
        WEIGHT_NEW = 0.3
        WEIGHT_OLD = 0.7

        if as_driver:
            self.rating_as_driver = round(
                (WEIGHT_OLD * self.rating_as_driver) + (WEIGHT_NEW * new_rating), 2
            )
        else:
            self.rating_as_passenger = round(
                (WEIGHT_OLD * self.rating_as_passenger) + (WEIGHT_NEW * new_rating), 2
            )
        self.save()


User = get_user_model()


class OTP(models.Model):
    TYPE_CHOICES = (
        ("EMAIL", "Email"),
        ("PASSWORD_RESET", "password_reset"),
        ("PHONE", "Phone"),
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, related_name="otp_codes"
    )
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="EMAIL")

    def __str__(self):
        return f"{self.type} OTP for {self.user.email} ({self.code}) - {'Verified' if self.is_verified else 'Pending'}"


    def is_valid(self):
        """Check if the OTP is still valid."""
        return (
            timezone.now() <= self.created_at + timedelta(minutes=10)
            and not self.is_verified
            and self.attempts < 3
        )

    @classmethod
    def create_otp_for_user(cls, user, otp_type="EMAIL"):
        """Create a new OTP for a user after marking previous unverified OTPs as verified."""
        # Mark previous unverified OTPs as verified
        cls.objects.filter(user=user, is_verified=False, type=otp_type).update(
            is_verified=True
        )

        # Generate a new OTP code
        otp_code = "".join([str(random.randint(0, 9)) for _ in range(6)])
        return cls.objects.create(user=user, code=otp_code, type=otp_type)

    def time_since_creation(self):
        """Returns the time elapsed since the OTP was created."""
        return timezone.now() - self.created_at
