"""Documentation source parsing, relevance filtering & ranked summary (R-17).

Optional pipeline that scores documentation sources against a user question,
filters by a configurable relevance threshold, ranks them, and produces a
spoken audio summary via TTS.

Enable/disable via ``source_analysis.enabled`` in ``assistant_config.yml``.
When disabled, no source analysis is performed.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from voice_agent.config import ConfigNode
from voice_agent.llm import LLMBackend
from voice_agent.prompt_loader import render_template


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SourceResult:
    """A single scored and described documentation source."""

    name: str
    score: float
    description: str
    content: str


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------


def is_source_analysis_enabled(config: ConfigNode) -> bool:
    """Check whether the source analysis pipeline is enabled.

    Returns ``True`` only when ``config.source_analysis.enabled`` is
    explicitly set to ``True``.  Defaults to ``False``.
    """
    sa = config.get("source_analysis")
    if sa is None:
        return False
    if isinstance(sa, dict):
        return bool(sa.get("enabled", False))
    return bool(getattr(sa, "enabled", False))


def _get_relevance_threshold(config: ConfigNode) -> float:
    """Return the relevance threshold from config (default 0.5)."""
    sa = config.get("source_analysis")
    if sa is None:
        return 0.5
    if isinstance(sa, dict):
        return float(sa.get("relevance_threshold", 0.5))
    return float(getattr(sa, "relevance_threshold", 0.5))


# ---------------------------------------------------------------------------
# Source loading
# ---------------------------------------------------------------------------


def load_source(source_path: str) -> dict[str, str]:
    """Load a single documentation source from a file path.

    Returns a dict with ``name`` (file name) and ``content`` (file text).
    If the file cannot be read, content will contain an error message.
    """
    path = Path(source_path)
    if not path.exists():
        return {"name": source_path, "content": f"[Error: file not found: {source_path}]"}
    try:
        text = path.read_text(encoding="utf-8")
        return {"name": path.name, "content": text}
    except (OSError, UnicodeDecodeError) as exc:
        return {"name": source_path, "content": f"[Error reading file: {exc}]"}


# ---------------------------------------------------------------------------
# Relevance scoring
# ---------------------------------------------------------------------------


def _parse_score_response(raw: str) -> dict[str, Any]:
    """Extract a JSON object from the LLM's scoring response.

    The LLM is instructed to return only ``{"score": ..., "description": ...}``
    but may wrap it in markdown fences or add commentary.  This function
    attempts to extract the first JSON object found.
    """
    # Strip markdown code fences if present
    cleaned = re.sub(r"```(?:json)?\s*", "", raw)
    cleaned = cleaned.replace("```", "").strip()

    # Try the whole string first
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        pass

    # Try to find a JSON object within the text
    match = re.search(r"\{[^}]+\}", cleaned)
    if match:
        try:
            return json.loads(match.group())
        except (json.JSONDecodeError, ValueError):
            pass

    # Fallback: treat as irrelevant
    return {"score": 0.0, "description": "Unable to parse relevance score."}


def score_source(
    question: str,
    source_name: str,
    source_content: str,
    llm: LLMBackend,
) -> tuple[float, str]:
    """Score a single source for relevance to the user's question.

    Returns ``(score, description)`` where score is 0.0–1.0.
    """
    try:
        prompt_text = render_template(
            "source_relevance_prompt",
            variables={
                "question": question,
                "source_name": source_name,
                "source_content": source_content,
            },
        )
    except FileNotFoundError:
        prompt_text = (
            f"Rate the relevance of this source to the question on a 0.0–1.0 scale.\n"
            f"Respond with ONLY JSON: {{\"score\": 0.0, \"description\": \"...\"}}\n\n"
            f"Question: {question}\n\nSource: {source_name}\n{source_content}"
        )

    messages = [
        {"role": "system", "content": prompt_text},
        {"role": "user", "content": "Score this source's relevance."},
    ]
    raw = llm.chat(messages)
    parsed = _parse_score_response(raw)

    score = max(0.0, min(1.0, float(parsed.get("score", 0.0))))
    description = str(parsed.get("description", ""))
    return score, description


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------


def analyze_sources(
    question: str,
    sources: list[str],
    llm: LLMBackend,
    config: ConfigNode,
) -> list[SourceResult]:
    """Run the full source analysis pipeline.

    1. Load each source file.
    2. Score each source against the question.
    3. Filter by the configured relevance threshold.
    4. Rank by score descending.

    Returns an empty list if source analysis is disabled or no sources
    pass the threshold.
    """
    if not is_source_analysis_enabled(config):
        return []

    if not sources:
        return []

    threshold = _get_relevance_threshold(config)
    results: list[SourceResult] = []

    for source_path in sources:
        loaded = load_source(source_path)
        name = loaded["name"]
        content = loaded["content"]

        # Skip sources that failed to load
        if content.startswith("[Error"):
            continue

        score, description = score_source(question, name, content, llm)

        if score >= threshold:
            results.append(
                SourceResult(
                    name=name,
                    score=score,
                    description=description,
                    content=content,
                )
            )

    # Rank by score descending
    results.sort(key=lambda r: r.score, reverse=True)
    return results


def build_ranked_summary(results: list[SourceResult]) -> str:
    """Build a plain-text ranked summary of source results.

    This summary is suitable for passing to TTS for audio delivery.
    """
    if not results:
        return "No relevant sources were found for your question."

    lines: list[str] = []
    for i, r in enumerate(results, 1):
        lines.append(f"{i}. {r.name} (score: {r.score:.1f}): {r.description}")

    return "\n".join(lines)


def build_ranked_audio_summary(
    results: list[SourceResult],
    llm: LLMBackend,
) -> str:
    """Generate a natural spoken summary of ranked sources via the LLM.

    Uses the ``source_summary_prompt`` XML template to produce a
    conversational audio-ready summary.
    """
    if not results:
        return "I didn't find any relevant sources for your question."

    ranked_text = build_ranked_summary(results)

    try:
        prompt_text = render_template(
            "source_summary_prompt",
            variables={"ranked_sources": ranked_text},
        )
    except FileNotFoundError:
        prompt_text = (
            "Summarise the following ranked sources for spoken audio delivery. "
            "Be conversational, mention each source by name with its relevance, "
            "and keep it concise.\n\n" + ranked_text
        )

    messages = [
        {"role": "system", "content": prompt_text},
        {"role": "user", "content": "Summarise the ranked sources for me."},
    ]
    return llm.chat(messages)
