from typing import Optional, Union
from apps.auths.models import User
from apps.core.models import Business

from utils.helpers.logs import logger

class BusinessUtil:

    @classmethod
    def create_business(
        cls, user: User, data: dict
    ) -> Business:
        """creates a vendor business"""
        country = data.get("country", "").title()
        # TODO: use a mapping of countries and their currencies
        # in order to update currency, in case none is provided
        # Also, get the coordinate of the business address and save in the _location column
        business = Business.objects.create(owner=user, **data)
        if country == "Nigeria":
            business.currency = "NGN"
        business.save()
        return business
