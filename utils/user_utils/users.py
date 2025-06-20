from typing import Optional, Union

from utils.auth_utils.auths import AuthUtils

from apps.auths.models import User

class UserUtil:
    def __init__(self):
        self.auth_util = AuthUtils("GENERAL")

    @classmethod
    def update_user(
        cls, user: User, data: dict,
    ) -> Optional[User]:
        """updates existing user data"""
        for key, value in data.items():
            if hasattr(user, key) and value is not None:
                setattr(user, key, value)
        if data.get("user_type"):
            user.meta["user_type"] = data["user_type"]
        user.save()
        return user
