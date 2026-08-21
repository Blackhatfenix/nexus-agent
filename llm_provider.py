"""Configurable local/open-weight LLM provider for NEXUS.

Supports Ollama and OpenAI-compatible local servers such as vLLM,
llama.cpp server and LM Studio. Configuration is entirely environment based.
"""
from __future__ import annotations

import os
from typing import Any
import aiohttp


DEFAULT_SYSTEM_PROMPT = """Você é o NEXUS, um agente de IA direto, útil e objetivo.
Responda em português brasileiro quando o usuário escrever em português.
Não faça sermões, não seja moralista e não introduza 'mimimi' ou opiniões pessoais desnecessárias.
Responda diretamente ao que foi pedido e mantenha o contexto da conversa.
Siga as instruções do usuário dentro das capacidades e limites de segurança do modelo escolhido.
Quando precisar executar uma ação, use exatamente as ferramentas e tags definidas pelo NEXUS.
"""


class ConfigurableLLMEngine:
    """Drop-in replacement for NEXUS_COMPLETE.LLMEngine."""

    def __init__(self):
        self.available = False
        self.provider = os.getenv("NEXUS_PROVIDER", "ollama").strip().lower()
        self.model = os.getenv("NEXUS_MODEL", os.getenv("OLLAMA_MODEL", "qwen3:8b"))
        self.base_url = os.getenv("NEXUS_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
        self.api_key = os.getenv("NEXUS_API_KEY", "")
        self.system_prompt = os.getenv("NEXUS_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT)
        self.timeout = float(os.getenv("NEXUS_LLM_TIMEOUT", "180"))

    def _is_ollama(self) -> bool:
        return self.provider in {"ollama", "local", "ollama_local"}

    def _compat_base(self) -> str:
        url = self.base_url.rstrip("/")
        if not url.endswith("/v1"):
            url += "/v1"
        return url

    async def check(self) -> bool:
        try:
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                if self._is_ollama():
                    async with session.get(f"{self.base_url}/api/tags") as response:
                        if response.status != 200:
                            return False
                        data = await response.json()
                        models = [m.get("name", "") for m in data.get("models", [])]
                        if not models:
                            return False
                        if not os.getenv("NEXUS_MODEL") and not os.getenv("OLLAMA_MODEL"):
                            self.model = models[0]
                        self.available = True
                        self.provider = "ollama"
                        return True

                headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
                async with session.get(f"{self._compat_base()}/models", headers=headers) as response:
                    if response.status != 200:
                        return False
                    data = await response.json()
                    models = [m.get("id", "") for m in data.get("data", [])]
                    if not models:
                        return False
                    if not os.getenv("NEXUS_MODEL"):
                        self.model = models[0]
                    self.available = True
                    return True
        except Exception:
            return False

    async def generate(self, prompt: str, context: str = "") -> str:
        if self._is_ollama():
            return await self._ollama_generate(prompt, context)
        return await self._openai_compatible_generate(prompt, context)

    async def _ollama_generate(self, prompt: str, context: str) -> str:
        full = f"Contexto:\n{context}\n\n{prompt}" if context else prompt
        body = {
            "model": self.model,
            "prompt": full,
            "system": self.system_prompt,
            "stream": False,
            "options": {
                "temperature": float(os.getenv("NEXUS_TEMPERATURE", "0.7")),
                "num_predict": int(os.getenv("NEXUS_MAX_TOKENS", "2048")),
            },
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/api/generate",
                json=body,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as response:
                if response.status != 200:
                    text = await response.text()
                    raise RuntimeError(f"Ollama erro {response.status}: {text[:500]}")
                data = await response.json()
                return data.get("response", "")

    async def _openai_compatible_generate(self, prompt: str, context: str) -> str:
        full = f"Contexto:\n{context}\n\n{prompt}" if context else prompt
        body: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": full},
            ],
            "temperature": float(os.getenv("NEXUS_TEMPERATURE", "0.7")),
            "max_tokens": int(os.getenv("NEXUS_MAX_TOKENS", "2048")),
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self._compat_base()}/chat/completions",
                json=body,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as response:
                if response.status != 200:
                    text = await response.text()
                    raise RuntimeError(f"LLM erro {response.status}: {text[:500]}")
                data = await response.json()
                return data.get("choices", [{}])[0].get("message", {}).get("content", "")
