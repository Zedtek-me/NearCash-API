import graphene
from graphene import Enum, ObjectType


class SignInWithEnum(Enum):
    """
    Enum for different sign-in methods.
    """
    GOOGLE = "google"
    FACEBOOK = "facebook"
    EMAIL_PASSWORD = "email_password"

class UserTypeEnum(Enum):
    """
    Enum for user types.
    """
    CLIENT = "CLIENT"
    VENDOR = "VENDOR"
    ADMIN = "ADMIN"
