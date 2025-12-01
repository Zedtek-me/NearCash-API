from typing import Optional, Union

from utils.auth_utils.auths import AuthUtils
from utils.core_utils.business_utils import BusinessUtil
from utils.helpers.logs import logger

from apps.auths.models import User
from apps.auths.schema.types.enums import UserTypeEnum

class UserUtil:
    def __init__(self):
        self.auth_util = AuthUtils("GENERAL")

    @classmethod
    def update_user(
        cls, user: User, data: dict
    ) -> Optional[User]:
        """updates existing user data"""
        user_type = user.meta.get("user_type") or cls._parse_user_type(data.pop("user_type", None)) #use user default type for now, pending the implementation of user_type update
        first_time = cls.check_first_time(user)
        picture_url = data.pop("picture", None) or user.meta.get("picture")
        phone_number = data.pop("phone_number", None)
        for key, value in data.items():
            if hasattr(user, key) and value is not None:
                setattr(user, key, value)
        user.meta.update({"user_type": user_type, "picture": picture_url})
        user.save()
        if phone_number and hasattr(user, "profile"):
            user.profile.phone_number = phone_number
            user.profile.save()
        if user_type == "VENDOR" and first_time:
            business_data = data.pop("business_data", {})
            BusinessUtil.create_business(
                user, cls.prepare_business_data(business_data)
            )
        return user

    @classmethod
    def prepare_business_data(
        cls, data: dict
    ) -> dict:
        """prepares data for business creation"""
        business_name = data.pop("business_name", None)
        business_data = {
            "name": business_name,
            **data
        }
        return business_data

    @classmethod
    def check_first_time(
        cls, user: User
    ) -> bool:
        """checks if user is first time"""
        from apps.core.models import Business
        if Business.objects.filter(owner=user).exists():
            return False
        return True

    @classmethod
    def _parse_user_type(
        cls, user_type: Union[UserTypeEnum, str]
    ) -> str:
        try:
            return user_type.name
        except Exception as e:
            logger.exception(f"Error parsing user type: {e}")
        return "CLIENT"
