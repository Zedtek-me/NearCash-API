from dataclasses import dataclass
from typing import Optional, List

@dataclass
class EmailArgsDto:
    subject: str
    body: str
    recipients: list
    context: Optional[dict]
    attchments: Optional[List[dict]]
