from typing import Union, Optional
from django.core.exceptions import ValidationError

class Validator:

    @classmethod
    def validate_number(cls, value: Union[float, int, str]) -> Union[bool, float]:
        """validates the given value is a number"""
        try:
            return float(value)
        except (ValueError, TypeError) as e:
            raise ValidationError("invalid number") from e
