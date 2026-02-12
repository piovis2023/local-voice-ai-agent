"""Conversation history management (R-02).

Maintains a list of {role, content} messages for the current session.
Supports a configurable max_turns cap to prevent context overflow.
"""

from __future__ import annotations

from typing import Any


class ConversationHistory:
    """In-memory conversation history with a configurable turn limit.

    Parameters
    ----------
    max_turns:
        Maximum number of *user+assistant* exchanges to keep.  Each exchange
        counts as two messages (one user, one assistant).  The system message
        (if any) is always preserved and does not count toward the limit.
        Set to 0 or ``None`` to disable the cap.
    """

    def __init__(self, max_turns: int = 20) -> None:
        self._messages: list[dict[str, str]] = []
        self.max_turns = max_turns

    @property
    def messages(self) -> list[dict[str, str]]:
        """Return the current message list (read-only copy)."""
        return list(self._messages)

    def add(self, role: str, content: str) -> None:
        """Append a message and enforce the turn cap."""
        self._messages.append({"role": role, "content": content})
        self._enforce_limit()

    def get_messages_for_llm(self) -> list[dict[str, str]]:
        """Return messages formatted for LLM consumption."""
        return list(self._messages)

    def clear(self) -> None:
        """Reset the conversation history."""
        self._messages.clear()

    def __len__(self) -> int:
        return len(self._messages)

    def _enforce_limit(self) -> None:
        """Trim oldest non-system messages when we exceed max_turns."""
        if not self.max_turns:
            return

        # Separate system messages from the rest
        system_msgs = [m for m in self._messages if m["role"] == "system"]
        non_system = [m for m in self._messages if m["role"] != "system"]

        max_non_system = self.max_turns * 2  # each turn = user + assistant
        if len(non_system) > max_non_system:
            non_system = non_system[-max_non_system:]

        self._messages = system_msgs + non_system
