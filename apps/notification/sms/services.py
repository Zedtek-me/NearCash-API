from django.conf import settings

from interfaces.general.notifications import SMSInterface

from dtos.generics import SMSPlatformDto

from utils.helpers.exception import CustomException


class SMSService(SMSInterface):

    platform_name: str = settings.DEFAULT_SMS_PLATFORM_NAME
    platform: SMSPlatformDto | None = None

    def __init__(self, platform_name: str | None = None):
        if platform_name:
            self.platform_name = platform_name

        # initializes the self.platform attribute
        self._initialize_sms_platform(self.platform_name)


    @classmethod
    def send(
        cls, content: dict | str | int | float,
        recipient_ids: list
    ) -> bool:

        if not cls.platform:
            raise CustomException(
                message="sms platform is not configured!"
            )
        cls.platform.send_sms(
            content, recipient_ids
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
