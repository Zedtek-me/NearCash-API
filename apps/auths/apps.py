from django.apps import AppConfig


class AuthsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.auths'

    def ready(self):
        from apps.auths import signals
        return super().ready()
