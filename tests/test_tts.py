"""Tests for the TTS abstraction layer (R-07, R-18–R-23)."""

import sys
import pytest
from unittest.mock import MagicMock, patch

from voice_agent.config import ConfigNode
from voice_agent.tts import (
    ChatterboxTTS,
    KokoroTTS,
    Pyttsx3TTS,
    RealtimeTTSBackend,
    TTSBackend,
    _chunk_text,
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


# ---------------------------------------------------------------------------
# ChatterboxTTS tests (R-18 — R-23)
# ---------------------------------------------------------------------------


class TestChatterboxInstantiation:
    """R-18: ChatterboxTTS instantiation and parameter forwarding."""

    def test_default_params(self):
        backend = ChatterboxTTS(voice_file="/tmp/ref.wav")
        assert backend.voice_file == "/tmp/ref.wav"
        assert backend.model_type == "original"
        assert backend.device_preference == "auto"
        assert backend.exaggeration == 0.5
        assert backend.cfg_weight == 0.5

    def test_turbo_model_type(self):
        backend = ChatterboxTTS(voice_file="/tmp/ref.wav", model_type="turbo")
        assert backend.model_type == "turbo"

    def test_rsxdalv_faster_model_type(self):
        backend = ChatterboxTTS(voice_file="/tmp/ref.wav", model_type="rsxdalv-faster")
        assert backend.model_type == "rsxdalv-faster"

    def test_custom_emotion_params(self):
        backend = ChatterboxTTS(
            voice_file="/tmp/ref.wav", exaggeration=0.8, cfg_weight=0.3,
        )
        assert backend.exaggeration == 0.8
        assert backend.cfg_weight == 0.3

    def test_invalid_model_type_raises(self):
        with pytest.raises(ValueError, match="Unknown Chatterbox model_type"):
            ChatterboxTTS(voice_file="/tmp/ref.wav", model_type="nonexistent")

    def test_repr(self):
        backend = ChatterboxTTS(voice_file="/tmp/ref.wav")
        assert "ChatterboxTTS" in repr(backend)

    def test_lazy_model_not_loaded(self):
        backend = ChatterboxTTS(voice_file="/tmp/ref.wav")
        assert backend._model is None


class TestChatterboxProviderRegistry:
    """R-18: ChatterboxTTS registered in _PROVIDERS."""

    def test_registered_as_chatterbox(self):
        from voice_agent.tts import _PROVIDERS
        assert "chatterbox" in _PROVIDERS
        assert _PROVIDERS["chatterbox"] is ChatterboxTTS

    def test_factory_returns_chatterbox(self):
        config = ConfigNode({
            "tts": {
                "provider": "chatterbox",
                "voice_file": "/tmp/ref.wav",
                "model_type": "original",
                "device": "cpu",
            },
        })
        backend = get_tts_backend(config)
        assert isinstance(backend, ChatterboxTTS)
        assert backend.voice_file == "/tmp/ref.wav"
        assert backend.model_type == "original"

    def test_factory_forwards_all_params(self):
        config = ConfigNode({
            "tts": {
                "provider": "chatterbox",
                "voice_file": "/tmp/ref.wav",
                "model_type": "turbo",
                "device": "cuda",
                "exaggeration": 0.9,
                "cfg_weight": 0.1,
            },
        })
        backend = get_tts_backend(config)
        assert isinstance(backend, ChatterboxTTS)
        assert backend.model_type == "turbo"
        assert backend.device_preference == "cuda"
        assert backend.exaggeration == 0.9
        assert backend.cfg_weight == 0.1

    def test_factory_rsxdalv_faster(self):
        config = ConfigNode({
            "tts": {
                "provider": "chatterbox",
                "voice_file": "/tmp/ref.wav",
                "model_type": "rsxdalv-faster",
                "device": "auto",
            },
        })
        backend = get_tts_backend(config)
        assert isinstance(backend, ChatterboxTTS)
        assert backend.model_type == "rsxdalv-faster"


class TestChatterboxVoiceValidation:
    """R-21: Voice file validation."""

    def test_missing_voice_file_param(self):
        backend = ChatterboxTTS()
        with pytest.raises(ValueError, match="voice_file"):
            backend._validate_voice_file()

    def test_voice_file_not_found(self):
        backend = ChatterboxTTS(voice_file="/nonexistent/path/voice.wav")
        with pytest.raises(FileNotFoundError, match="not found"):
            backend._validate_voice_file()

    def test_voice_file_wrong_extension(self, tmp_path):
        mp3_file = tmp_path / "voice.mp3"
        mp3_file.write_bytes(b"fake audio data")
        backend = ChatterboxTTS(voice_file=str(mp3_file))
        with pytest.raises(ValueError, match=".wav"):
            backend._validate_voice_file()

    def test_voice_file_empty(self, tmp_path):
        wav_file = tmp_path / "empty.wav"
        wav_file.write_bytes(b"")
        backend = ChatterboxTTS(voice_file=str(wav_file))
        with pytest.raises(ValueError, match="empty"):
            backend._validate_voice_file()

    def test_voice_file_valid(self, tmp_path):
        wav_file = tmp_path / "voice.wav"
        wav_file.write_bytes(b"RIFF....WAVEfmt ")
        backend = ChatterboxTTS(voice_file=str(wav_file))
        path = backend._validate_voice_file()
        assert path == wav_file


class TestChatterboxLazyImport:
    """R-20: Lazy import guard."""

    def test_import_error_original(self):
        backend = ChatterboxTTS(voice_file="/tmp/ref.wav", model_type="original")
        with patch.dict(sys.modules, {"chatterbox": None, "chatterbox.tts": None}):
            with pytest.raises(RuntimeError, match="pip install --no-deps chatterbox-tts"):
                backend._load_model()

    def test_import_error_turbo(self):
        backend = ChatterboxTTS(voice_file="/tmp/ref.wav", model_type="turbo")
        with patch.dict(sys.modules, {"chatterbox": None, "chatterbox.tts": None}):
            with pytest.raises(RuntimeError, match="pip install --no-deps chatterbox-tts"):
                backend._load_model()

    def test_import_error_rsxdalv_faster(self):
        backend = ChatterboxTTS(voice_file="/tmp/ref.wav", model_type="rsxdalv-faster")
        with patch.dict(sys.modules, {"chatterbox": None, "chatterbox.tts": None}):
            with pytest.raises(RuntimeError, match="rsxdalv/chatterbox.git@faster"):
                backend._load_model()


class TestChatterboxTextChunking:
    """R-22: Sentence-boundary text chunking."""

    def test_empty_text(self):
        assert _chunk_text("") == []

    def test_whitespace_only(self):
        assert _chunk_text("   ") == []

    def test_short_text_single_chunk(self):
        text = "Hello world."
        chunks = _chunk_text(text)
        assert chunks == ["Hello world."]

    def test_long_text_splits_at_sentence(self):
        # Build a text > 500 chars with clear sentence boundaries
        s1 = "A" * 300 + "."
        s2 = "B" * 300 + "."
        text = f"{s1} {s2}"
        chunks = _chunk_text(text, limit=500)
        assert len(chunks) == 2
        assert chunks[0] == s1
        assert chunks[1] == s2

    def test_single_long_sentence_not_broken(self):
        sentence = "A" * 800 + "."
        chunks = _chunk_text(sentence, limit=500)
        assert len(chunks) == 1
        assert chunks[0] == sentence

    def test_multiple_sentences_packed(self):
        text = "One. Two. Three. Four. Five."
        chunks = _chunk_text(text, limit=100)
        # All fit in one chunk
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_question_and_exclamation_splits(self):
        s1 = "X" * 300 + "?"
        s2 = "Y" * 300 + "!"
        text = f"{s1} {s2}"
        chunks = _chunk_text(text, limit=500)
        assert len(chunks) == 2


class TestChatterboxStreamTTS:
    """R-18: stream_tts() end-to-end with mocked model."""

    def _make_mock_model(self):
        mock_model = MagicMock()
        # Return a mock tensor that mimics the torch.Tensor chaining API.
        # squeeze() -> cpu() -> numpy() -> astype() must all resolve.
        fake_audio = MagicMock()
        fake_audio.astype.return_value = fake_audio  # .astype(np.float32)
        fake_tensor = MagicMock()
        fake_tensor.squeeze.return_value = fake_tensor
        fake_tensor.cpu.return_value = fake_tensor
        fake_tensor.numpy.return_value = fake_audio
        mock_model.generate.return_value = fake_tensor
        return mock_model

    def _make_mock_np(self):
        """Create a fake numpy module so stream_tts can import it."""
        mock_np = MagicMock()
        mock_np.float32 = "float32"
        mock_np.asarray.side_effect = lambda v, dtype=None: v
        return mock_np

    def test_stream_tts_original(self, tmp_path):
        wav = tmp_path / "voice.wav"
        wav.write_bytes(b"RIFF....WAVEfmt ")

        backend = ChatterboxTTS(
            voice_file=str(wav), model_type="original", device="cpu",
        )
        mock_model = self._make_mock_model()
        backend._model = mock_model

        with patch.dict(sys.modules, {"numpy": self._make_mock_np()}):
            chunks = list(backend.stream_tts("Hello world."))
        assert len(chunks) == 1
        sr, audio = chunks[0]
        assert sr == 24000
        mock_model.generate.assert_called_once()
        call_kwargs = mock_model.generate.call_args
        assert call_kwargs[1]["exaggeration"] == 0.5
        assert call_kwargs[1]["cfg_weight"] == 0.5

    def test_stream_tts_turbo(self, tmp_path):
        wav = tmp_path / "voice.wav"
        wav.write_bytes(b"RIFF....WAVEfmt ")

        backend = ChatterboxTTS(
            voice_file=str(wav), model_type="turbo", device="cpu",
        )
        mock_model = self._make_mock_model()
        backend._model = mock_model

        with patch.dict(sys.modules, {"numpy": self._make_mock_np()}):
            chunks = list(backend.stream_tts("Hello world."))
        assert len(chunks) == 1
        call_kwargs = mock_model.generate.call_args
        # Turbo does NOT pass exaggeration/cfg_weight
        assert "exaggeration" not in call_kwargs[1]
        assert "cfg_weight" not in call_kwargs[1]

    def test_stream_tts_rsxdalv_faster(self, tmp_path):
        wav = tmp_path / "voice.wav"
        wav.write_bytes(b"RIFF....WAVEfmt ")

        backend = ChatterboxTTS(
            voice_file=str(wav), model_type="rsxdalv-faster", device="cpu",
        )
        mock_model = self._make_mock_model()
        backend._model = mock_model

        with patch.dict(sys.modules, {"numpy": self._make_mock_np()}):
            chunks = list(backend.stream_tts("Hello world."))
        assert len(chunks) == 1
        # rsxdalv-faster uses same API as original (with exaggeration/cfg_weight)
        call_kwargs = mock_model.generate.call_args
        assert "exaggeration" in call_kwargs[1]

    def test_stream_tts_long_text_chunked(self, tmp_path):
        wav = tmp_path / "voice.wav"
        wav.write_bytes(b"RIFF....WAVEfmt ")

        backend = ChatterboxTTS(
            voice_file=str(wav), model_type="original", device="cpu",
        )
        mock_model = self._make_mock_model()
        backend._model = mock_model

        # Build text > 500 chars with 2 sentences
        long_text = ("A" * 300 + ". ") + ("B" * 300 + ".")
        with patch.dict(sys.modules, {"numpy": self._make_mock_np()}):
            chunks = list(backend.stream_tts(long_text))
        assert len(chunks) == 2
        assert mock_model.generate.call_count == 2
