from django.contrib.auth.models import BaseUserManager
from django.core.exceptions import ValidationError

class UserManager(BaseUserManager):

    def __init__(self, *args, **kwargs):
        self.active = kwargs.pop('active', True)
        super().__init__(*args, **kwargs)

    def get_queryset(self):
        if self.active:
            return super().get_queryset().filter(status="ACTIVE")
        return super().get_queryset()

    def create_user(self, **kwargs):
        if not "email" in kwargs:
            raise ValidationError("email is required!")
        password = kwargs.pop("password")
        user = self.model(email=self.clean(kwargs.get("email")), **kwargs)
        user.is_active = True
        if password:
            user.set_password(password)
        user.save()
        return user

    def create_superuser(self, **kwargs):
        user = self.create_user(**kwargs)
        user.is_superuser = True
        user.is_staff = True
        user.save()
        return user
