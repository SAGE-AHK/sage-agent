from fastapi import FastAPI
from pydantic import BaseModel
from agent import SageAgent
import threading

app = FastAPI(title="SAGE Agent API")

agent = SageAgent(
    event_name="Entrega de Diplomas AHK 2026",
    event_location="Centro de Convenciones, Av. Corrientes, Buenos Aires",
    event_date="15 de Agosto de 2026"
)

class MessageRequest(BaseModel):
    mensaje: str

class MessageResponse(BaseModel):
    respuesta: str
    historial_length: int

@app.get("/")
def root():
    return {"status": "EVA online"}

@app.post("/chat", response_model=MessageResponse)
def chat(request: MessageRequest):
    respuesta = agent.chat(request.mensaje)
    return MessageResponse(
        respuesta=respuesta,
        historial_length=len(agent.history)
    )

@app.post("/reset")
def reset():
    threading.Thread(target=agent.reset).start()
    return {"status": "Sesión reiniciada, warm-up en proceso"}
