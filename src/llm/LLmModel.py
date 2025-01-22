from openai import OpenAI
import os
from typing import List
from langchain_openai import ChatOpenAI


class LLmModel:
    @staticmethod
    def getModel():
        return OpenAI(
            api_key=os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1",
        )

    @staticmethod
    def getLangchainChatModel():
        return ChatOpenAI(
            api_key=os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1",
            model="llama3-8b-8192",
        )
