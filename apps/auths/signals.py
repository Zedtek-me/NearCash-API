from django.db.models.signals import post_save
from apps.auths.models import User, UserProfile


def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

post_save.connect(
    create_user_profile, sender=User
)
