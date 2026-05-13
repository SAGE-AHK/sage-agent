import json
import uuid
from datetime import datetime
from pathlib import Path

FEEDBACK_FILE = Path(__file__).parent / "feedback_log.json"

FEEDBACK_KEYWORDS = [
    "estuvo", "me gustó", "no me gustó", "excelente", "malo", "bueno",
    "mejorar", "perfecto", "horrible", "increíble", "aburrido", "largo",
    "corto", "organización", "ceremonia", "catering", "comida", "música",
    "feedback", "opinión", "experiencia", "felicitar", "queja", "problema"
]

CATEGORY_KEYWORDS = {
    "ceremonia": ["ceremonia", "diploma", "entrega", "discurso", "palabras"],
    "organización": ["organización", "puntualidad", "orden", "espera", "demora"],
    "recepción": ["recepción", "entrada", "acreditación", "bienvenida", "llegada"],
    "catering": ["catering", "comida", "bebida", "buffet", "networking"],
}

def is_feedback(message: str) -> bool:
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in FEEDBACK_KEYWORDS)

def detect_category(message: str) -> str:
    message_lower = message.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in message_lower for kw in keywords):
            return category
    return "general"

def detect_sentiment(message: str) -> str:
    positive = ["bueno", "excelente", "increíble", "perfecto", "me gustó",
                "genial", "fantástico", "felicitar", "muy bien", "estuvo bien"]
    negative = ["malo", "horrible", "no me gustó", "mejorar", "queja",
                "problema", "demora", "largo", "aburrido", "desorganizado"]
    msg = message.lower()
    pos = sum(1 for w in positive if w in msg)
    neg = sum(1 for w in negative if w in msg)
    if pos > neg:
        return "positivo"
    elif neg > pos:
        return "negativo"
    return "neutro"

def save_feedback(session_id: str, user_message: str, eva_response: str):
    entry = {
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "timestamp": datetime.now().isoformat(),
        "mensaje_invitado": user_message,
        "respuesta_eva": eva_response,
        "categoria": detect_category(user_message),
        "sentimiento": detect_sentiment(user_message)
    }

    existing = []
    if FEEDBACK_FILE.exists():
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
            existing = json.load(f)

    existing.append(entry)

    with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    print(f"[EVA] Feedback guardado — categoría: {entry['categoria']}, sentimiento: {entry['sentimiento']}")
    return entry
