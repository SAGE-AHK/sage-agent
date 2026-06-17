import threading
from typing import Callable

from agent import SageAgent
from embeddings import IntentMatcher

DEFAULT_ROL = "asistente"
DEFAULT_TOTEM_ID = "default"
VALID_ROLES = {"asistente", "recepcionista"}


def normalize_rol(rol: str | None) -> str:
    rol = (rol or DEFAULT_ROL).strip().lower()
    if rol not in VALID_ROLES:
        print(f"[EVA] Rol desconocido '{rol}', usando '{DEFAULT_ROL}' por defecto.")
        return DEFAULT_ROL
    return rol


def normalize_totem_id(totem_id: str | None) -> str:
    return (totem_id or DEFAULT_TOTEM_ID).strip() or DEFAULT_TOTEM_ID


class AgentManager:
    """
    Mantiene un SageAgent independiente por cada combinación (rol, totem_id),
    permitiendo múltiples conversaciones simultáneas — varios tótems del
    mismo rol o de roles distintos — sobre un único modelo de Ollama.
    """

    def __init__(self, prompt_resolver: Callable[[str], str]):
        self._prompt_resolver = prompt_resolver
        self._matcher: IntentMatcher | None = None
        self._matcher_lock = threading.Lock()
        self._agents: dict[str, SageAgent] = {}
        self._locks: dict[str, threading.Lock] = {}
        self._registry_lock = threading.Lock()

    def _get_shared_matcher(self) -> IntentMatcher:
        if self._matcher is None:
            with self._matcher_lock:
                if self._matcher is None:
                    self._matcher = IntentMatcher()
        return self._matcher

    @staticmethod
    def _key(rol: str, totem_id: str) -> str:
        return f"{rol}:{totem_id}"

    def get_agent(self, rol: str, totem_id: str) -> SageAgent:
        key = self._key(rol, totem_id)
        agent = self._agents.get(key)
        if agent is None:
            with self._registry_lock:
                agent = self._agents.get(key)
                if agent is None:
                    print(f"[EVA] Creando nueva sesión — rol={rol} totem={totem_id}")
                    prompt = self._prompt_resolver(rol)
                    agent = SageAgent(
                        system_prompt=prompt,
                        matcher=self._get_shared_matcher(),
                        rol=rol,
                    )
                    self._agents[key] = agent
                    self._locks[key] = threading.Lock()
        return agent

    def get_lock(self, rol: str, totem_id: str) -> threading.Lock:
        key = self._key(rol, totem_id)
        return self._locks.setdefault(key, threading.Lock())

    def reset(self, rol: str, totem_id: str) -> None:
        agent = self.get_agent(rol, totem_id)
        with self.get_lock(rol, totem_id):
            agent.reset()

    def invalidate_all(self) -> None:
        """Borra todas las sesiones activas — usado cuando se reconfigura el evento."""
        with self._registry_lock:
            self._agents.clear()
            self._locks.clear()
        print("[EVA] Todas las sesiones invalidadas — se recrearán con el nuevo prompt.")

    def status(self) -> list[dict]:
        return [
            {"key": key, "rol": agent.rol, "historial_length": len(agent.history)}
            for key, agent in self._agents.items()
        ]