from django.contrib.auth.models import BaseUserManager

class UserManager(BaseUserManager):

    def __init__(self, *args, **kwargs):
        self.active = kwargs.pop('active', True)
        super().__init__(*args, **kwargs)

    def get_queryset(self):
        if self.active:
            return super().get_queryset().filter(status="ACTIVE")
        return super().get_queryset()
