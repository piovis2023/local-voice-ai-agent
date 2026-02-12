"""Dual assistant mode architecture (R-08).

Implements ``chat`` and ``agent`` modes, each with its own prompt pipeline.
Both modes share the same STT/TTS/LLM backends.  The active mode is selected
via ``config.mode`` in ``assistant_config.yml``.
"""

from __future__ import annotations

import abc
from typing import Any

from voice_agent.config import ConfigNode
from voice_agent.context import context_prompt_section
from voice_agent.history import ConversationHistory
from voice_agent.llm import LLMBackend, get_llm_backend
from voice_agent.prompt_loader import render_template
from voice_agent.scratchpad import scratchpad_prompt_section


class ModeHandler(abc.ABC):
    """Base class for assistant operating modes.

    Each mode builds its own system prompt from a different XML template
    but shares the same LLM backend, conversation history, and
    scratchpad/context infrastructure.

    Parameters
    ----------
    config:
        The loaded application config.
    llm:
        An instantiated LLM backend.  If ``None``, one is created from *config*.
    context_files:
        Optional list of file paths to inject as reference material.
    """

    def __init__(
        self,
        config: ConfigNode,
        llm: LLMBackend | None = None,
        context_files: list[str] | None = None,
    ) -> None:
        self.config = config
        self.llm = llm or get_llm_backend(config)
        self.context_files = context_files or []
        conv = config.get("conversation")
        max_turns = conv.get("max_turns", 20) if isinstance(conv, dict) else 20
        self.history = ConversationHistory(max_turns=max_turns)
        # Build and inject the mode-specific system prompt
        system_prompt = self.build_system_prompt()
        self.history.add("system", system_prompt)

    @abc.abstractmethod
    def build_system_prompt(self) -> str:
        """Return the fully-rendered system prompt for this mode."""

    def handle_turn(self, user_input: str) -> str:
        """Process one conversational turn.

        Adds the user message to history, queries the LLM, records the
        assistant response, and returns it.
        """
        self.history.add("user", user_input)
        response = self.llm.chat(self.history.get_messages_for_llm())
        self.history.add("assistant", response)
        return response

    @property
    def mode_name(self) -> str:
        """Return a human-readable mode identifier."""
        return self.__class__.__name__

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(llm={self.llm!r})"


class ChatMode(ModeHandler):
    """Conversational chat mode.

    Uses the ``system_prompt`` XML template.  Enhances the current chat
    behaviour with history, scratchpad memory, and context file injection.
    """

    def build_system_prompt(self) -> str:
        sp_conf = self.config.get("scratchpad")
        sp_file = sp_conf.get("file") if isinstance(sp_conf, dict) else None
        scratchpad = scratchpad_prompt_section(sp_file)
        context = context_prompt_section(self.context_files)

        try:
            return render_template(
                "system_prompt",
                variables={
                    "assistant_name": self.config.assistant.name,
                    "persona": self.config.assistant.persona,
                    "scratchpad": scratchpad,
                    "context": context,
                },
            )
        except FileNotFoundError:
            return self.config.assistant.persona + scratchpad + context

    @property
    def mode_name(self) -> str:
        return "chat"


class AgentMode(ModeHandler):
    """Agentic command execution mode.

    Uses the ``agent_command_prompt`` XML template.  The LLM is instructed
    to translate voice input into CLI commands.  Actual command execution is
    handled by the execution layer (Phase 5).

    Parameters
    ----------
    commands:
        A string listing available Typer commands to inject into the prompt.
    """

    def __init__(
        self,
        config: ConfigNode,
        llm: LLMBackend | None = None,
        context_files: list[str] | None = None,
        commands: str = "",
    ) -> None:
        self.commands = commands
        super().__init__(config, llm=llm, context_files=context_files)

    def build_system_prompt(self) -> str:
        sp_conf = self.config.get("scratchpad")
        sp_file = sp_conf.get("file") if isinstance(sp_conf, dict) else None
        scratchpad = scratchpad_prompt_section(sp_file)
        context = context_prompt_section(self.context_files)

        try:
            return render_template(
                "agent_command_prompt",
                variables={
                    "assistant_name": self.config.assistant.name,
                    "commands": self.commands,
                    "scratchpad": scratchpad,
                    "context": context,
                },
            )
        except FileNotFoundError:
            return (
                f"You are {self.config.assistant.name} in command mode.\n"
                f"Available commands: {self.commands}\n"
                + scratchpad
                + context
            )

    @property
    def mode_name(self) -> str:
        return "agent"


# ---------------------------------------------------------------------------
# Mode registry & factory
# ---------------------------------------------------------------------------

_MODES: dict[str, type[ModeHandler]] = {
    "chat": ChatMode,
    "agent": AgentMode,
}


def get_mode_handler(
    config: ConfigNode,
    llm: LLMBackend | None = None,
    context_files: list[str] | None = None,
    **kwargs: Any,
) -> ModeHandler:
    """Instantiate the mode handler specified in ``config.mode``.

    Parameters
    ----------
    config:
        Application configuration (must have a ``mode`` attribute).
    llm:
        Optional pre-built LLM backend to share across modes.
    context_files:
        Optional context file paths for prompt injection.
    **kwargs:
        Extra keyword arguments forwarded to the mode constructor
        (e.g. ``commands`` for agent mode).

    Raises
    ------
    ValueError
        If the configured mode is not recognised.
    """
    mode = config.get("mode", "chat").lower()

    cls = _MODES.get(mode)
    if cls is None:
        raise ValueError(
            f"Unknown mode: {mode!r}. Available: {', '.join(sorted(_MODES))}"
        )

    return cls(config=config, llm=llm, context_files=context_files, **kwargs)
