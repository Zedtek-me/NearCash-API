import graphene
from graphene import ObjectType
from graphene_django import DjangoObjectType

from apps.auths.models import User
from apps.auths.schema.types.enums import UserTypeEnum
from apps.core.schema.types.business_types import CreateBusinessInputType

from utils.helpers.logs import logger


class UserType(DjangoObjectType):
    class Meta:
        model = User
        fields = "__all__"
    user_type = graphene.String()
    full_name = graphene.String()
    phone_number = graphene.String()
    profile_picture = graphene.String()

    def resolve_user_type(self, info):
        return self.meta.get("user_type", "CLIENT")

    def resolve_full_name(self, info):
        return self.full_name

    def resolve_phone_number(self, info):
        try:
            return self.profile.phone_number
        except Exception as e:
            logger.error(f"Error fetching phone number for user {self.id}: {e}")
            return None

    def resolve_profile_picture(self, info):
        try:
            return self.profile.profile_picture
        except Exception as e:
            logger.error(f"Error fetching profile picture for user {self.id}: {e}")
            return None


class LoginInfoType(ObjectType):
    """
    Type for login information.
    """
    user = graphene.Field(UserType, required=False)
    token = graphene.String(required=False)
    auth_url = graphene.String(required=False)


class AuthInputType(graphene.InputObjectType):
    email = graphene.String()
    first_name = graphene.String(required=False)
    last_name = graphene.String(required=False)
    username = graphene.String(required=False)
    password = graphene.String()

class UpdateUserInputType(graphene.InputObjectType):
    user_type = UserTypeEnum(required=False)
    first_name = graphene.String(required=False)
    last_name = graphene.String(required=False)
    username = graphene.String(required=False)
    picture = graphene.String(required=False)
    phone_number = graphene.String(required=False)
    bvn = graphene.String(required=False)
    nin = graphene.String(required=False)
    remittance_bank_code = graphene.String(required=False)
    remittance_bank_name = graphene.String(required=False)
    remittance_account_number = graphene.String(required=False)

    # business data
    business_data = CreateBusinessInputType(required=False)
