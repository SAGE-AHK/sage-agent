import requests
import json
from prompts import get_prompt

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2:3b"

class SageAgent:
    def __init__(self, event_name: str, event_location: str, event_date: str):
        self.system_prompt = get_prompt(event_name, event_location, event_date)
        self.history = []

    def chat(self, user_message: str) -> str:
        self.history.append({
            "role": "user",
            "content": user_message
        })

        payload = {
            "model": MODEL,
            "stream": False,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                *self.history
            ]
        }

        response = requests.post(OLLAMA_URL, json=payload)
        response.raise_for_status()

        assistant_message = response.json()["message"]["content"]

        self.history.append({
            "role": "assistant",
            "content": assistant_message
        })

        return assistant_message

    def reset(self):
        self.history = []
