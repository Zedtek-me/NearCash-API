from dataclasses import dataclass
from typing import Union, Optional


@dataclass
class CreateBusinessDto:
    business_name: str
    address: Optional[str]
    country: Optional[str]
    description: Optional[str]
    parent_address_id: Optional[str]

@dataclass
class UpdateBusinessDto(CreateBusinessDto):
    business_name: Optional[str]
