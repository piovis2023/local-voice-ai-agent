"""Tests for the documentation source analysis pipeline (R-17)."""

import json
import pytest
from unittest.mock import MagicMock, patch

from voice_agent.config import ConfigNode
from voice_agent.source_analysis import (
    SourceResult,
    _get_relevance_threshold,
    _parse_score_response,
    analyze_sources,
    build_ranked_audio_summary,
    build_ranked_summary,
    is_source_analysis_enabled,
    load_source,
    score_source,
)


# ---------------------------------------------------------------------------
# Config helper tests
# ---------------------------------------------------------------------------


def test_source_analysis_disabled_by_default():
    """When no source_analysis section exists, analysis is disabled."""
    config = ConfigNode({"llm": {"provider": "ollama"}})
    assert is_source_analysis_enabled(config) is False


def test_source_analysis_disabled_explicitly():
    """Source analysis can be explicitly disabled."""
    config = ConfigNode({"source_analysis": {"enabled": False}})
    assert is_source_analysis_enabled(config) is False


def test_source_analysis_enabled():
    """Source analysis is enabled when config flag is True."""
    config = ConfigNode({"source_analysis": {"enabled": True}})
    assert is_source_analysis_enabled(config) is True


def test_default_relevance_threshold():
    """Default relevance threshold is 0.5."""
    config = ConfigNode({})
    assert _get_relevance_threshold(config) == 0.5


def test_custom_relevance_threshold():
    """Relevance threshold can be configured."""
    config = ConfigNode({"source_analysis": {"enabled": True, "relevance_threshold": 0.7}})
    assert _get_relevance_threshold(config) == 0.7


# ---------------------------------------------------------------------------
# Source loading tests
# ---------------------------------------------------------------------------


def test_load_source_existing_file(tmp_path):
    """load_source reads file content correctly."""
    f = tmp_path / "doc.txt"
    f.write_text("This is documentation content.")

    result = load_source(str(f))
    assert result["name"] == "doc.txt"
    assert result["content"] == "This is documentation content."


def test_load_source_missing_file():
    """load_source returns an error entry for missing files."""
    result = load_source("/nonexistent/file.txt")
    assert "[Error" in result["content"]
    assert "not found" in result["content"]


# ---------------------------------------------------------------------------
# Score response parsing tests
# ---------------------------------------------------------------------------


def test_parse_score_response_clean_json():
    """Parses a clean JSON response."""
    raw = '{"score": 0.8, "description": "Highly relevant."}'
    result = _parse_score_response(raw)
    assert result["score"] == 0.8
    assert result["description"] == "Highly relevant."


def test_parse_score_response_with_markdown_fences():
    """Parses JSON wrapped in markdown code fences."""
    raw = '```json\n{"score": 0.6, "description": "Moderately relevant."}\n```'
    result = _parse_score_response(raw)
    assert result["score"] == 0.6


def test_parse_score_response_with_surrounding_text():
    """Extracts JSON from surrounding commentary."""
    raw = 'Here is my assessment: {"score": 0.3, "description": "Low relevance."} Done.'
    result = _parse_score_response(raw)
    assert result["score"] == 0.3


def test_parse_score_response_invalid():
    """Returns fallback for completely unparseable responses."""
    raw = "I cannot parse this at all."
    result = _parse_score_response(raw)
    assert result["score"] == 0.0
    assert "Unable to parse" in result["description"]


# ---------------------------------------------------------------------------
# score_source tests
# ---------------------------------------------------------------------------


def test_score_source_returns_score_and_description():
    """score_source returns a (score, description) tuple."""
    llm = MagicMock()
    llm.chat.return_value = '{"score": 0.9, "description": "Very relevant content."}'

    score, desc = score_source("How to deploy?", "deploy.md", "Deploy instructions...", llm)

    assert score == 0.9
    assert desc == "Very relevant content."
    llm.chat.assert_called_once()


def test_score_source_clamps_to_valid_range():
    """Scores outside 0.0–1.0 are clamped."""
    llm = MagicMock()
    llm.chat.return_value = '{"score": 1.5, "description": "Over the top."}'

    score, _ = score_source("q", "f.txt", "content", llm)
    assert score == 1.0

    llm.chat.return_value = '{"score": -0.2, "description": "Negative."}'
    score, _ = score_source("q", "f.txt", "content", llm)
    assert score == 0.0


def test_score_source_fallback_without_template():
    """score_source works even if the template file is missing."""
    llm = MagicMock()
    llm.chat.return_value = '{"score": 0.5, "description": "Fallback."}'

    with patch("voice_agent.source_analysis.render_template", side_effect=FileNotFoundError):
        score, desc = score_source("q", "f.txt", "content", llm)

    assert score == 0.5
    assert desc == "Fallback."


# ---------------------------------------------------------------------------
# analyze_sources tests
# ---------------------------------------------------------------------------


def _make_config(enabled: bool = True, threshold: float = 0.5) -> ConfigNode:
    return ConfigNode({
        "source_analysis": {
            "enabled": enabled,
            "relevance_threshold": threshold,
        },
    })


def test_analyze_sources_disabled():
    """Returns empty list when source analysis is disabled."""
    config = _make_config(enabled=False)
    llm = MagicMock()
    result = analyze_sources("question", ["file.txt"], llm, config)
    assert result == []
    llm.chat.assert_not_called()


def test_analyze_sources_empty_list():
    """Returns empty list when no sources are provided."""
    config = _make_config()
    llm = MagicMock()
    result = analyze_sources("question", [], llm, config)
    assert result == []


def test_analyze_sources_filters_below_threshold(tmp_path):
    """Sources below the threshold are filtered out."""
    doc_high = tmp_path / "high.txt"
    doc_high.write_text("Very relevant documentation.")
    doc_low = tmp_path / "low.txt"
    doc_low.write_text("Unrelated content.")

    config = _make_config(threshold=0.5)
    llm = MagicMock()
    llm.chat.side_effect = [
        '{"score": 0.9, "description": "Very relevant."}',
        '{"score": 0.2, "description": "Not relevant."}',
    ]

    results = analyze_sources("How to deploy?", [str(doc_high), str(doc_low)], llm, config)

    assert len(results) == 1
    assert results[0].name == "high.txt"
    assert results[0].score == 0.9


def test_analyze_sources_ranks_by_score(tmp_path):
    """Sources are ranked by score descending."""
    doc_a = tmp_path / "a.txt"
    doc_a.write_text("Content A.")
    doc_b = tmp_path / "b.txt"
    doc_b.write_text("Content B.")
    doc_c = tmp_path / "c.txt"
    doc_c.write_text("Content C.")

    config = _make_config(threshold=0.3)
    llm = MagicMock()
    llm.chat.side_effect = [
        '{"score": 0.5, "description": "Medium."}',
        '{"score": 0.9, "description": "High."}',
        '{"score": 0.7, "description": "Good."}',
    ]

    results = analyze_sources(
        "question", [str(doc_a), str(doc_b), str(doc_c)], llm, config
    )

    assert len(results) == 3
    assert results[0].name == "b.txt"
    assert results[1].name == "c.txt"
    assert results[2].name == "a.txt"


def test_analyze_sources_skips_unreadable_files(tmp_path):
    """Sources that fail to load are silently skipped."""
    doc = tmp_path / "good.txt"
    doc.write_text("Valid content.")

    config = _make_config(threshold=0.3)
    llm = MagicMock()
    llm.chat.return_value = '{"score": 0.8, "description": "Relevant."}'

    results = analyze_sources(
        "question", ["/nonexistent.txt", str(doc)], llm, config
    )

    assert len(results) == 1
    assert results[0].name == "good.txt"


# ---------------------------------------------------------------------------
# build_ranked_summary tests
# ---------------------------------------------------------------------------


def test_build_ranked_summary_with_results():
    """Builds a numbered text summary of results."""
    results = [
        SourceResult("deploy.md", 0.9, "Deployment guide.", "..."),
        SourceResult("config.md", 0.6, "Configuration reference.", "..."),
    ]
    summary = build_ranked_summary(results)
    assert "1. deploy.md" in summary
    assert "2. config.md" in summary
    assert "0.9" in summary
    assert "0.6" in summary


def test_build_ranked_summary_empty():
    """Returns a message when no results are available."""
    summary = build_ranked_summary([])
    assert "No relevant sources" in summary


# ---------------------------------------------------------------------------
# build_ranked_audio_summary tests
# ---------------------------------------------------------------------------


def test_build_ranked_audio_summary_calls_llm():
    """build_ranked_audio_summary sends ranked sources through the LLM."""
    llm = MagicMock()
    llm.chat.return_value = "Okay, so I found 2 relevant sources."

    results = [
        SourceResult("deploy.md", 0.9, "Deployment guide.", "..."),
        SourceResult("config.md", 0.6, "Config reference.", "..."),
    ]

    summary = build_ranked_audio_summary(results, llm)
    assert summary == "Okay, so I found 2 relevant sources."
    llm.chat.assert_called_once()


def test_build_ranked_audio_summary_empty():
    """Returns a fallback message when no results exist."""
    llm = MagicMock()
    summary = build_ranked_audio_summary([], llm)
    assert "didn't find" in summary
    llm.chat.assert_not_called()


def test_build_ranked_audio_summary_fallback_without_template():
    """Falls back gracefully when the template file is missing."""
    llm = MagicMock()
    llm.chat.return_value = "Here is a summary."

    results = [SourceResult("doc.md", 0.8, "Relevant.", "...")]

    with patch("voice_agent.source_analysis.render_template", side_effect=FileNotFoundError):
        summary = build_ranked_audio_summary(results, llm)

    assert summary == "Here is a summary."
    llm.chat.assert_called_once()


# ---------------------------------------------------------------------------
# SourceResult dataclass tests
# ---------------------------------------------------------------------------


def test_source_result_is_frozen():
    """SourceResult is immutable."""
    result = SourceResult("doc.md", 0.8, "Relevant.", "Content.")
    with pytest.raises(AttributeError):
        result.score = 0.5


def test_source_result_fields():
    """SourceResult stores all fields correctly."""
    result = SourceResult(
        name="guide.md",
        score=0.75,
        description="Useful guide.",
        content="Full content here.",
    )
    assert result.name == "guide.md"
    assert result.score == 0.75
    assert result.description == "Useful guide."
    assert result.content == "Full content here."
