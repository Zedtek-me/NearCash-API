from django.conf import settings

from interfaces.general.notifications import SMSInterface

from dtos.generics import SMSPlatformDto

from utils.helpers.exception import CustomException

from celery import shared_task

from apps.auths.models import User, UserProfile


class SMSService(SMSInterface):

    platform_name: str = settings.DEFAULT_SMS_PLATFORM_NAME
    platform: SMSPlatformDto | None = None

    def __init__(self, platform_name: str | None = None):
        if platform_name:
            self.platform_name = platform_name

        # initializes the self.platform attribute
        self._initialize_sms_platform(self.platform_name)


    @shared_task(
        name="send.sms", bind=True
    )
    def send_sms(
        self, content: dict | str | int | float,
        recipient_msisdn: list[str | int]
    ) -> bool:
        """
        send sms
        """

        if not SMSService.platform:
            raise CustomException(
                message="sms platform is not configured!"
            )
        SMSService.platform.send_sms(
            content, recipient_msisdn
        )
        return True


    def _initialize_sms_platform(
        self, platform_name: str
    ) -> SMSPlatformDto:
        self.platform = self._get_platform_configs(platform_name)
        return self.platform


    def _get_platform_configs(
        self, platform_name: str
    ) -> SMSPlatformDto:
        # other attributes will be populated after instantiation
        return SMSPlatformDto(
            platform_name, "", {}
        )
