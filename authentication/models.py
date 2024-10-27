from django.db import models
from django.contrib.auth.models import AbstractUser

# we didnt unique username cause multiple people have the same name right, so the email is unique
#password isnt mentioned here cause its already in the abstract user
class User(AbstractUser):
    email = models.EmailField(unique=True)
    username = None
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

