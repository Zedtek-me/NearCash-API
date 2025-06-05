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
    password = models.CharField(max_length=128, blank=True)
    status = models.CharField(max_length=20, default='ACTIVE', choices=STATUSES)

    objects = UserManager(active=True)
    all_objects = UserManager(active=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'username']

    class Meta:
        db_table = 'user'
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return f"{self.first_name} -> {self.last_name} -> ({self.email})"
