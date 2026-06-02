# src/rag/llm_client.py
#
# Minimal pluggable LLM interface. Default implementation talks to a local
# Ollama server — fully free, no API key, no deprecation/rate-limit risk.
# A cloud provider could be slotted in later behind the same interface via
# config, without touching any caller.

import json

import httpx
from loguru import logger

from src.utils.config import config


class LLMUnavailable(RuntimeError):
    """Raised when the configured LLM backend cannot be reached."""


class OllamaClient:
    """Wraps the local Ollama HTTP API (/api/chat)."""

    def __init__(self, base_url: str | None = None, model: str | None = None,
                 timeout: float | None = None):
        self.base_url = (base_url or config.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or config.OLLAMA_MODEL
        self.timeout = timeout or config.LLM_TIMEOUT

    def is_available(self) -> bool:
        """True if the Ollama server is up and the model has been pulled."""
        try:
            resp = httpx.get(f"{self.base_url}/api/tags", timeout=5)
            resp.raise_for_status()
            names = [m.get("name", "") for m in resp.json().get("models", [])]
            # Match "llama3.2" against "llama3.2:latest" etc.
            return any(n == self.model or n.startswith(f"{self.model}:") for n in names)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Ollama not available at {self.base_url}: {e}")
            return False

    def generate(self, prompt: str, system: str | None = None,
                 json_mode: bool = False) -> str:
        """
        Send a single-turn chat request and return the assistant text.
        Raises LLMUnavailable on connection/HTTP failure.
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        body = {"model": self.model, "messages": messages, "stream": False}
        if json_mode:
            body["format"] = "json"

        try:
            resp = httpx.post(f"{self.base_url}/api/chat", json=body, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()["message"]["content"]
        except Exception as e:  # noqa: BLE001
            raise LLMUnavailable(f"Ollama generation failed: {e}") from e

    def generate_json(self, prompt: str, system: str | None = None) -> dict:
        """Generate with JSON mode and parse; returns {} if parsing fails."""
        raw = self.generate(prompt, system=system, json_mode=True)
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            logger.warning("LLM JSON parse failed; returning empty dict")
            return {}


def get_llm() -> OllamaClient:
    """Factory — the single place that decides which LLM backend to use."""
    return OllamaClient()


if __name__ == "__main__":
    llm = get_llm()
    print("Available:", llm.is_available())
    if llm.is_available():
        print(llm.generate("Say 'TK-Shield online' and nothing else."))
