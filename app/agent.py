import requests
import uuid
from prompts import get_prompt
from feedback import is_feedback, save_feedback

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2:3b"

class SageAgent:
    def __init__(self, event_name: str, event_location: str, event_date: str):
        self.system_prompt = get_prompt(event_name, event_location, event_date)
        self.history = []
        self.session_id = str(uuid.uuid4())
        self._warm_up()

    def _warm_up(self):
        try:
            payload = {
                "model": MODEL,
                "stream": False,
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": "hola"},
                ]
            }
            response = requests.post(OLLAMA_URL, json=payload, timeout=60)
            response.raise_for_status()
            print("[EVA] Warm-up completado. Modelo listo.")
        except Exception as e:
            print(f"[EVA] Warm-up falló: {e}")

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

        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        response.raise_for_status()

        assistant_message = response.json()["message"]["content"]

        self.history.append({
            "role": "assistant",
            "content": assistant_message
        })

        if is_feedback(user_message):
            save_feedback(self.session_id, user_message, assistant_message)

        return assistant_message

    def reset(self):
        self.history = []
        self.session_id = str(uuid.uuid4())
        self._warm_up()
