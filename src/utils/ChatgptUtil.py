from openai import AsyncOpenAI
import json
import asyncio


class ChatGPTHandler:
    def __init__(
        self,
        api_key,
        model="llama3-8b-8192",
    ):
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
        )
        self.model = model

    async def ask_chatgpt(self, websocket, question, context=None):
        """
        Send a question to ChatGPT and stream the response back through websocket.

        Args:
            websocket: WebSocket connection to send responses
            question (str): The question to ask ChatGPT
            context (str, optional): Any additional context to provide
        """
        try:
            messages = []
            if context:
                messages.append({"role": "system", "content": context})

            messages.append({"role": "user", "content": question})

            # Create streaming response
            stream = await self.client.chat.completions.create(
                model=self.model,  # or your preferred model
                messages=messages,
                stream=True,
            )

            # Initialize response tracking
            full_response = ""

            # Stream the response chunks
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content

                    # Send chunk through websocket
                    await websocket.send_text(
                        json.dumps({"type": "chatgpt_chunk", "content": content})
                    )

            # Send completion message
            await websocket.send_text(
                json.dumps({"type": "chatgpt_complete", "full_response": full_response})
            )

        except Exception as e:
            # Send error message
            await websocket.send_text(
                json.dumps({"type": "chatgpt_error", "error": str(e)})
            )
