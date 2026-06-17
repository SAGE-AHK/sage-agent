import json
import uuid
from datetime import datetime
from pathlib import Path
import os

DATA_DIR = Path(os.getenv("SAGE_DATA_DIR", "/app/data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

FEEDBACK_FILE = DATA_DIR / "feedback_log.json"

def save_feedback(session_id: str, user_message: str, eva_response: str, category: str = "general", rol: str = "asistente"):
    entry = {
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "rol": rol,
        "timestamp": datetime.now().isoformat(),
        "mensaje_invitado": user_message,
        "respuesta_eva": eva_response,
        "categoria": category,
    }

    existing = []
    if FEEDBACK_FILE.exists():
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
            existing = json.load(f)

    existing.append(entry)

    with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    print(f"[EVA] Feedback guardado — rol: {rol} — categoría: {category}")
    return entry