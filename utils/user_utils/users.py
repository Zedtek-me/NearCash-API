from typing import Optional, Union

from utils.auth_utils.auths import AuthUtils
from utils.core_utils.business_utils import BusinessUtil
from utils.helpers.logs import logger

from apps.auths.models import User
from apps.auths.schema.types.enums import UserTypeEnum
from apps.auths.models import UserProfile

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
        bvn = data.pop("bvn", None)
        nin = data.pop("nin", None)
        remittance_bank_code = data.pop("remittance_bank_code", None)
        remittance_bank_name = data.pop("remittance_bank_name", None)
        remittance_account_number = data.pop("remittance_account_number", None)
        for key, value in data.items():
            if hasattr(user, key) and value is not None:
                setattr(user, key, value)
        user.meta.update({"user_type": user_type, "picture": picture_url})
        user.save()
        profile, _ = UserProfile.objects.get_or_create(user=user)
        # other profile data updates
        cls._update_other_profile_data(
            profile, bvn=bvn, nin=nin,
            remittance_account_number=remittance_account_number,
            remittance_bank_name=remittance_bank_name,
            remittance_bank_code=remittance_bank_code,
            phone_number=phone_number,
            profile_picture=picture_url
        )
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


    @classmethod
    def fetch_user_thirdparty_customer_info(
        cls, user: User, thirdparty: str = "flutterwave"
    ) -> dict:
        """
        returns the customer information of a user previously recorded on a
        thirdparty system -- payment system
        """
        profile, _ = UserProfile.objects.get_or_create(user=user)
        return (profile.thirdparty_payment_customer_info or {}).get(thirdparty, {})


    @classmethod
    def _update_other_profile_data(
        cls, profile: UserProfile, **data
    ) -> UserProfile:
        for key, value in data.items():
            if hasattr(profile, key) and value is not None:
                setattr(profile, key, value)
        profile.save()
        return profile
