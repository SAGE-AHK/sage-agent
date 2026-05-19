import requests
import uuid
from prompts import get_prompt
from feedback import is_feedback, save_feedback

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2:3b"
REQUEST_TIMEOUT = 30

TOKEN_LIMITS = {
    "lista": 400,
    "detalle": 250,
    "simple": 150,
}

LIST_TRIGGERS = [
    "todos", "todas", "quiénes", "quienes", "listar", "lista",
    "egresados de", "chicos de", "integrantes", "área de", "area de",
    "trabajaron en", "hay egresados", "carreras", "contame sobre los",
    "contame sobre las", "cuántos", "cuantos"
]

DETAIL_TRIGGERS = [
    "contame sobre", "háblame de", "hablame de", "quién es", "quien es",
    "datos de", "información de", "informacion de", "perfil de",
    "hobbies", "proyecto de", "qué hizo", "que hizo"
]

def get_token_limit(message: str) -> int:
    msg = message.lower()
    if any(t in msg for t in LIST_TRIGGERS):
        return TOKEN_LIMITS["lista"]
    if any(t in msg for t in DETAIL_TRIGGERS):
        return TOKEN_LIMITS["detalle"]
    return TOKEN_LIMITS["simple"]

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
                "options": {"num_predict": TOKEN_LIMITS["simple"]},
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
        blocked = self._check_jailbreak(user_message)
        if blocked:
            return blocked

        token_limit = get_token_limit(user_message)
        print(f"[EVA] Token limit para este mensaje: {token_limit}")

        self.history.append({
            "role": "user",
            "content": user_message
        })

        payload = {
            "model": MODEL,
            "stream": False,
            "options": {"num_predict": token_limit},
            "messages": [
                {"role": "system", "content": self.system_prompt},
                *self.history
            ]
        }

        try:
            response = requests.post(OLLAMA_URL, json=payload, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            assistant_message = response.json()["message"]["content"]
        except requests.exceptions.Timeout:
            self.history.pop()
            return "Disculpá, tardé demasiado en responder. ¿Podés repetirme tu pregunta?"
        except Exception as e:
            self.history.pop()
            print(f"[EVA] Error en chat: {e}")
            return "Hubo un problema al procesar tu mensaje. Enseguida consulto con el equipo."

        if is_feedback(user_message):
            save_feedback(self.session_id, user_message, assistant_message)

        self.history.append({
            "role": "assistant",
            "content": assistant_message
        })

        return assistant_message

    def _check_jailbreak(self, message: str) -> str | None:
        message_lower = message.lower()

        override_triggers = [
            "ignora", "ignorá", "olvida", "olvidá", "ignora las instrucciones",
            "instrucciones anteriores", "instrucciones previas", "eres ahora",
            "sos ahora", "actúa como", "actuá como", "nuevo rol", "nueva instrucción",
            "pretend", "you are now", "forget your", "ignore your",
            "ignora tu", "ignorá tu"
        ]

        language_triggers = [
            "speak english", "talk in english", "respond in english",
            "answer in english", "in english please", "en inglés",
            "hablá en inglés", "respondé en inglés", "habla en ingles",
            "responde en ingles"
        ]

        fabrication_triggers = [
            "inventá", "inventa", "imaginá", "imagina", "suponé", "supone",
            "hacé como si", "hace como si", "fingí", "fingi",
            "decime algo falso", "inventate", "inventate algo"
        ]

        if any(t in message_lower for t in override_triggers):
            return "Solo puedo ayudarte con información del evento. ¿En qué te puedo asistir?"
        if any(t in message_lower for t in language_triggers):
            return "Mi idioma de atención es el español. ¿En qué puedo ayudarte?"
        if any(t in message_lower for t in fabrication_triggers):
            return "Solo puedo darte información real del evento. ¿Tenés alguna consulta?"

        return None

    def reset(self):
        self.history = []
        self.session_id = str(uuid.uuid4())
        self._warm_up()
