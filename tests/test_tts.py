"""Tests for the TTS abstraction layer (R-07)."""

import sys
import pytest
from unittest.mock import MagicMock, patch

from voice_agent.config import ConfigNode
from voice_agent.tts import (
    KokoroTTS,
    Pyttsx3TTS,
    RealtimeTTSBackend,
    TTSBackend,
    get_tts_backend,
)


# ---------------------------------------------------------------------------
# Base class tests
# ---------------------------------------------------------------------------


def test_tts_backend_is_abstract():
    """TTSBackend cannot be instantiated directly."""
    with pytest.raises(TypeError):
        TTSBackend(voice="test")


# ---------------------------------------------------------------------------
# KokoroTTS tests
# ---------------------------------------------------------------------------


def test_kokoro_repr():
    """KokoroTTS has a meaningful repr."""
    backend = KokoroTTS(voice="af_heart")
    assert "KokoroTTS" in repr(backend)
    assert "af_heart" in repr(backend)


def test_kokoro_default_voice():
    """KokoroTTS defaults to af_heart."""
    backend = KokoroTTS()
    assert backend.voice == "af_heart"


def test_kokoro_stream_tts():
    """KokoroTTS.stream_tts() delegates to FastRTC's TTS model."""
    mock_model = MagicMock()
    mock_model.stream_tts_sync.return_value = [(24000, b"audio_chunk")]

    mock_fastrtc = MagicMock()
    mock_fastrtc.get_tts_model.return_value = mock_model

    with patch.dict(sys.modules, {"fastrtc": mock_fastrtc}):
        backend = KokoroTTS(voice="af_heart")
        chunks = list(backend.stream_tts("Hello world"))

    assert len(chunks) == 1
    assert chunks[0] == (24000, b"audio_chunk")
    mock_model.stream_tts_sync.assert_called_once_with("Hello world")


def test_kokoro_lazy_init():
    """KokoroTTS lazily initializes the model on first use."""
    mock_model = MagicMock()
    mock_model.stream_tts_sync.return_value = []

    mock_fastrtc = MagicMock()
    mock_fastrtc.get_tts_model.return_value = mock_model

    backend = KokoroTTS()
    assert backend._model is None

    with patch.dict(sys.modules, {"fastrtc": mock_fastrtc}):
        list(backend.stream_tts("test"))
        assert backend._model is not None
        mock_fastrtc.get_tts_model.assert_called_once()

        # Second call reuses the model
        list(backend.stream_tts("test2"))
        mock_fastrtc.get_tts_model.assert_called_once()


# ---------------------------------------------------------------------------
# Pyttsx3TTS tests
# ---------------------------------------------------------------------------


def test_pyttsx3_repr():
    """Pyttsx3TTS has a meaningful repr."""
    backend = Pyttsx3TTS(voice="english")
    assert "Pyttsx3TTS" in repr(backend)


def test_pyttsx3_default_voice():
    """Pyttsx3TTS defaults to None voice."""
    backend = Pyttsx3TTS()
    assert backend.voice is None


def test_pyttsx3_stores_rate():
    """Pyttsx3TTS stores rate from kwargs."""
    backend = Pyttsx3TTS(rate=200)
    assert backend._rate == 200


# ---------------------------------------------------------------------------
# RealtimeTTSBackend tests
# ---------------------------------------------------------------------------


def test_realtimetts_repr():
    """RealtimeTTSBackend has a meaningful repr."""
    backend = RealtimeTTSBackend(voice="default")
    assert "RealtimeTTSBackend" in repr(backend)


def test_realtimetts_default_voice():
    """RealtimeTTSBackend defaults to None voice."""
    backend = RealtimeTTSBackend()
    assert backend.voice is None


# ---------------------------------------------------------------------------
# Factory tests
# ---------------------------------------------------------------------------


def test_get_tts_backend_kokoro():
    """get_tts_backend returns KokoroTTS for kokoro provider."""
    config = ConfigNode({
        "tts": {"provider": "kokoro", "voice": "af_heart"},
    })
    backend = get_tts_backend(config)
    assert isinstance(backend, KokoroTTS)
    assert backend.voice == "af_heart"


def test_get_tts_backend_pyttsx3():
    """get_tts_backend returns Pyttsx3TTS for pyttsx3 provider."""
    config = ConfigNode({
        "tts": {"provider": "pyttsx3", "voice": "english"},
    })
    backend = get_tts_backend(config)
    assert isinstance(backend, Pyttsx3TTS)
    assert backend.voice == "english"


def test_get_tts_backend_realtimetts():
    """get_tts_backend returns RealtimeTTSBackend for realtimetts provider."""
    config = ConfigNode({
        "tts": {"provider": "realtimetts", "voice": "default"},
    })
    backend = get_tts_backend(config)
    assert isinstance(backend, RealtimeTTSBackend)
    assert backend.voice == "default"


def test_get_tts_backend_forwards_extra_keys():
    """get_tts_backend forwards extra config keys like rate."""
    config = ConfigNode({
        "tts": {"provider": "pyttsx3", "voice": "english", "rate": 200},
    })
    backend = get_tts_backend(config)
    assert isinstance(backend, Pyttsx3TTS)
    assert backend._rate == 200


def test_get_tts_backend_unknown_provider():
    """get_tts_backend raises ValueError for unknown provider."""
    config = ConfigNode({
        "tts": {"provider": "unknown", "voice": "x"},
    })
    with pytest.raises(ValueError, match="Unknown TTS provider"):
        get_tts_backend(config)


def test_get_tts_backend_case_insensitive():
    """Provider name matching is case-insensitive."""
    config = ConfigNode({
        "tts": {"provider": "Kokoro", "voice": "af_heart"},
    })
    backend = get_tts_backend(config)
    assert isinstance(backend, KokoroTTS)
