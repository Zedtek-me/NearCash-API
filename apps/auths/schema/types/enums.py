import graphene
from graphene import Enum, ObjectType


class SignInWithEnum(Enum):
    """
    Enum for different sign-in methods.
    """
    GOOGLE = "google"
    FACEBOOK = "facebook"
    EMAIL_PASSWORD = "email_password"
