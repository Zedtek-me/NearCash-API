from typing import Optional

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin

from interfaces.managers.users import UserManager
from interfaces.models.base import BaseModel

class User(BaseModel, AbstractBaseUser, PermissionsMixin):
    STATUSES = (
        ("ACTIVE", "ACTIVE"),
        ("IN_ACTIVE", "IN_ACTIVE"),
        ("DELETED", "DELETED"),
    )
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    username = models.CharField(max_length=50)
    email = models.EmailField(unique=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    password = models.CharField(max_length=128, null=True)
    status = models.CharField(max_length=20, default='ACTIVE', choices=STATUSES)
    _channel = models.CharField(max_length=255, null=True)

    objects = UserManager(active=True)
    all_objects = UserManager(active=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'username', 'password']

    class Meta:
        db_table = 'user'
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return f"{self.first_name} -> {self.last_name} -> ({self.email})"

    @property
    def user_queue(self):
        """gets the user channel name"""
        return self._channel


    @user_queue.setter
    def user_queue(self, value: str):
        """Sets the user channel name."""
        self._channel = value
        self.save()


class SocialToken(BaseModel):
    """records social tokens"""
    TOKEN_SOURCES = (
        ("GOOGLE", "GOOGLE"),
        ("FACEBOOK", "FACEBOOK")
    )
    user = models.ForeignKey(
        to="auths.User", on_delete=models.CASCADE, null=True
    )
    source = models.CharField(max_length=255, blank=True, choices=TOKEN_SOURCES)
    access_token = models.TextField(blank=True)
    refresh_token = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "SocialToken"
        verbose_name_plural = "SocialTokens"
        db_table = "social_token"

    def __str__(self):
        return f"{self.source} token"

    @classmethod
    def fetch_instance(cls, return_all: Optional[bool]=False, **filter_params):
        """factory method to return its instance"""
        instances = cls.objects.filter(**filter_params)
        if return_all:
            return instances
        return instances.first()
