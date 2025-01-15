from dataclasses import dataclass
from datetime import datetime


@dataclass
class AssistantResponse:
    role: str
    content: str
    timestamp: str

    def __init__(self, role: str, content: str, timestamp: datetime):
        self.role = role
        self.content = content
        self.timestamp = timestamp.isoformat()
