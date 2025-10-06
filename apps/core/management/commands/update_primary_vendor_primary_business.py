from django.core.management.base import BaseCommand
from utils.helpers.logs import logger

class Command(BaseCommand):
    help = 'Update the first business create by vendors as their primary business'

    @staticmethod
    def handle(*args, **kwargs):
        from apps.core.models import Business
        from apps.auths.models import User

        vendors = User.objects.filter(meta__user_type='VENDOR')
        for vendor in vendors:
            logger.info(f"Setting primary business for vendor {vendor.full_name} ({vendor.id})")
            vendor_businesses = Business.objects.filter(owner__id=vendor.id).order_by('date_created')
            first_business = vendor_businesses.first()
            if first_business:
                first_business.is_primary = True
                first_business.save(update_fields=["is_primary"])
                logger.info(
                    f"Updated primary business for vendor {vendor.id} to business {first_business.id}"
                )
        logger.info('Successfully updated primary businesses for all vendors')
