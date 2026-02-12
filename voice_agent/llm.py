"""LLM abstraction layer with multi-backend support (R-06).

Provides a common ``chat(messages) -> str`` interface with swappable providers.
Provider and model are selected via ``assistant_config.yml``.
"""

from __future__ import annotations

import abc
from typing import Any

from voice_agent.config import ConfigNode


class LLMBackend(abc.ABC):
    """Base class for all LLM providers."""

    def __init__(self, model: str, **kwargs: Any) -> None:
        self.model = model

    @abc.abstractmethod
    def chat(self, messages: list[dict[str, str]]) -> str:
        """Send a conversation and return the assistant's reply as a string."""

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.model!r})"


class OllamaLLM(LLMBackend):
    """Ollama local LLM provider (default)."""

    def __init__(self, model: str = "gemma3:4b", **kwargs: Any) -> None:
        super().__init__(model, **kwargs)
        self._options = kwargs.get("options", {})

    def chat(self, messages: list[dict[str, str]]) -> str:
        import ollama

        response = ollama.chat(
            model=self.model,
            messages=messages,
            options=self._options,
        )
        return response["message"]["content"]


class DeepSeekLLM(LLMBackend):
    """DeepSeek API provider.

    Requires the ``DEEPSEEK_API_KEY`` environment variable or an ``api_key``
    kwarg.  Uses the OpenAI-compatible endpoint at ``api.deepseek.com``.
    """

    BASE_URL = "https://api.deepseek.com"

    def __init__(self, model: str = "deepseek-chat", **kwargs: Any) -> None:
        super().__init__(model, **kwargs)
        self._api_key: str | None = kwargs.get("api_key")

    def _get_client(self) -> Any:
        import os

        from openai import OpenAI

        api_key = self._api_key or os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            raise RuntimeError(
                "DeepSeek API key not found. Set the DEEPSEEK_API_KEY environment "
                "variable or pass api_key in the config."
            )
        return OpenAI(api_key=api_key, base_url=self.BASE_URL)

    def chat(self, messages: list[dict[str, str]]) -> str:
        client = self._get_client()
        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
        )
        return response.choices[0].message.content


class AnthropicLLM(LLMBackend):
    """Anthropic Claude API provider.

    Requires the ``ANTHROPIC_API_KEY`` environment variable or an ``api_key``
    kwarg.
    """

    def __init__(self, model: str = "claude-sonnet-4-20250514", **kwargs: Any) -> None:
        super().__init__(model, **kwargs)
        self._api_key: str | None = kwargs.get("api_key")
        self._max_tokens: int = kwargs.get("max_tokens", 1024)

    def _get_client(self) -> Any:
        import os

        import anthropic

        api_key = self._api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "Anthropic API key not found. Set the ANTHROPIC_API_KEY environment "
                "variable or pass api_key in the config."
            )
        return anthropic.Anthropic(api_key=api_key)

    def chat(self, messages: list[dict[str, str]]) -> str:
        client = self._get_client()

        # Anthropic API separates the system prompt from conversation messages.
        system_text = ""
        conversation: list[dict[str, str]] = []
        for msg in messages:
            if msg["role"] == "system":
                system_text += msg["content"] + "\n"
            else:
                conversation.append(msg)

        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self._max_tokens,
            "messages": conversation,
        }
        if system_text.strip():
            kwargs["system"] = system_text.strip()

        response = client.messages.create(**kwargs)
        return response.content[0].text


# ---------------------------------------------------------------------------
# Provider registry & factory
# ---------------------------------------------------------------------------

_PROVIDERS: dict[str, type[LLMBackend]] = {
    "ollama": OllamaLLM,
    "deepseek": DeepSeekLLM,
    "anthropic": AnthropicLLM,
}


def get_llm_backend(config: ConfigNode) -> LLMBackend:
    """Instantiate the LLM backend specified in the config.

    Reads ``config.llm.provider`` and ``config.llm.model`` to select and
    configure the appropriate backend.  Ollama is the default.
    """
    provider = getattr(config.llm, "provider", "ollama").lower()
    model = getattr(config.llm, "model", None)

    cls = _PROVIDERS.get(provider)
    if cls is None:
        raise ValueError(
            f"Unknown LLM provider: {provider!r}. "
            f"Available: {', '.join(sorted(_PROVIDERS))}"
        )

    kwargs: dict[str, Any] = {}
    # Forward any extra llm config keys (e.g. api_key, max_tokens, options)
    llm_data = config.llm.to_dict()
    for key, value in llm_data.items():
        if key not in ("provider", "model"):
            kwargs[key] = value

    if model:
        return cls(model=model, **kwargs)
    return cls(**kwargs)
