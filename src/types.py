from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4


@dataclass
class AssistantResponse:
    role: str
    content: str
    timestamp: str

    def __init__(self, role: str, content: str, timestamp: datetime):
        self.role = role
        self.content = content
        self.timestamp = timestamp.isoformat()


@dataclass
class InterviewHistory:
    role: str
    content: str
    question_type: str
    timestamp: str
    audio: str
    id: str

    def __init__(
        self,
        role: str,
        content: str,
        timestamp: datetime,
        question_type: str,
        audio: str = None,
        id: str = str(uuid4()),
    ):
        self.role = role
        self.content = content
        self.question_type = question_type
        self.timestamp = timestamp.isoformat()
        self.audio = audio
        self.id = id
