from src.constant import USER_DATA_PATH
from src.util import read_file
import json


class ResumeStorage:
    def __init__(self):
        self.resume = dict()

    def add_resume(self, user_id, resume):
        self.resume[user_id] = resume

    async def get_resume(self, user_id):
        if user_id not in self.resume:
            file = await read_file(f"{user_id}.json", USER_DATA_PATH)
            if not file:
                return False
            self.resume[user_id] = json.dumps(file)

        return self.resume.get(user_id)
