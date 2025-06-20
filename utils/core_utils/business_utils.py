from typing import Optional, Union
from apps.auths.models import User
from apps.core.models import Business

class BusinessUtil:

    @classmethod
    def create_business(
        cls, user: User, data: dict
    ) -> Business:
        """creates a vendor business"""
        business = Business.objects.create(**data)
        business.owner = user
        business.save()
        return business
