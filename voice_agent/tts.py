"""TTS abstraction layer with multi-backend support (R-07).

Provides a common ``stream_tts(text) -> Iterator[audio_chunk]`` interface with
swappable providers.  Provider is selected via ``assistant_config.yml``.
"""

from __future__ import annotations

import abc
import pathlib
import re
from typing import Any, Iterator

from voice_agent.config import ConfigNode


class TTSBackend(abc.ABC):
    """Base class for all TTS providers."""

    def __init__(self, voice: str | None = None, **kwargs: Any) -> None:
        self.voice = voice

    @abc.abstractmethod
    def stream_tts(self, text: str) -> Iterator[tuple[int, Any]]:
        """Yield ``(sample_rate, audio_array)`` chunks for the given text."""

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(voice={self.voice!r})"


class KokoroTTS(TTSBackend):
    """Kokoro local TTS provider (default).

    Wraps FastRTC's ``get_tts_model()`` which returns a Kokoro-backed model
    with a ``stream_tts_sync`` method.
    """

    def __init__(self, voice: str | None = "af_heart", **kwargs: Any) -> None:
        super().__init__(voice, **kwargs)
        self._model: Any = None

    def _get_model(self) -> Any:
        if self._model is None:
            from fastrtc import get_tts_model

            self._model = get_tts_model()
        return self._model

    def stream_tts(self, text: str) -> Iterator[tuple[int, Any]]:
        model = self._get_model()
        yield from model.stream_tts_sync(text)


class Pyttsx3TTS(TTSBackend):
    """pyttsx3 local TTS fallback provider.

    Uses the system's built-in speech synthesis engine.  Audio is generated
    in-memory and yielded as a single chunk.
    """

    def __init__(self, voice: str | None = None, **kwargs: Any) -> None:
        super().__init__(voice, **kwargs)
        self._rate: int = kwargs.get("rate", 150)

    def stream_tts(self, text: str) -> Iterator[tuple[int, Any]]:
        import os
        import tempfile
        import wave

        import numpy as np
        import pyttsx3

        engine = pyttsx3.init()
        engine.setProperty("rate", self._rate)

        if self.voice:
            voices = engine.getProperty("voices")
            for v in voices:
                if self.voice.lower() in v.id.lower():
                    engine.setProperty("voice", v.id)
                    break

        # Write to a unique temporary WAV file to avoid race conditions
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav_path = tmp.name

        try:
            engine.save_to_file(text, wav_path)
            engine.runAndWait()

            with wave.open(wav_path, "rb") as wf:
                sample_rate = wf.getframerate()
                frames = wf.readframes(wf.getnframes())
                audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
                yield (sample_rate, audio)
        except FileNotFoundError:
            raise RuntimeError("pyttsx3 failed to generate audio output.")
        finally:
            try:
                os.unlink(wav_path)
            except OSError:
                pass


class RealtimeTTSBackend(TTSBackend):
    """RealtimeTTS with SystemEngine provider.

    Uses the ``RealtimeTTS`` library's ``SystemEngine`` for streaming
    text-to-speech via the system's native TTS capabilities.
    """

    DEFAULT_SAMPLE_RATE = 22050

    def __init__(self, voice: str | None = None, **kwargs: Any) -> None:
        super().__init__(voice, **kwargs)
        self._sample_rate: int = kwargs.get("sample_rate", self.DEFAULT_SAMPLE_RATE)

    def stream_tts(self, text: str) -> Iterator[tuple[int, Any]]:
        import numpy as np
        from RealtimeTTS import SystemEngine, TextToAudioStream

        engine = SystemEngine()
        if self.voice:
            engine.set_voice(self.voice)

        stream = TextToAudioStream(engine)
        stream.feed(text)

        audio_chunks: list[bytes] = []

        def on_audio_chunk(chunk: bytes) -> None:
            audio_chunks.append(chunk)

        stream.play(on_audio_chunk=on_audio_chunk, muted=True)

        if audio_chunks:
            raw = b"".join(audio_chunks)
            audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
            yield (self._sample_rate, audio)


# ---------------------------------------------------------------------------
# Chatterbox TTS — voice cloning provider (R-18)
# ---------------------------------------------------------------------------

# Sentence-boundary regex for chunking long inputs (R-22).
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")

# Maximum characters per chunk before sentence-boundary splitting kicks in.
_CHUNK_CHAR_LIMIT = 500


def _chunk_text(text: str, limit: int = _CHUNK_CHAR_LIMIT) -> list[str]:
    """Split *text* into sentence-boundary chunks of at most *limit* chars.

    If a single sentence exceeds *limit* it is yielded as-is (never broken
    mid-sentence).  Empty inputs return an empty list.
    """
    if not text or not text.strip():
        return []
    sentences = _SENTENCE_SPLIT_RE.split(text.strip())
    chunks: list[str] = []
    current = ""
    for sent in sentences:
        if current and len(current) + 1 + len(sent) > limit:
            chunks.append(current)
            current = sent
        else:
            current = f"{current} {sent}".strip() if current else sent
    if current:
        chunks.append(current)
    return chunks


# Recognised model_type values and their install hints.
_CHATTERBOX_MODEL_TYPES = {"original", "turbo", "rsxdalv-faster"}


class ChatterboxTTS(TTSBackend):
    """Chatterbox TTS voice-cloning provider (R-18).

    Supports three model types selectable via ``model_type`` config:

    * ``"original"``  — official 0.5B model with emotion control.
    * ``"turbo"``     — official 350M 1-step diffusion (~6x real-time).
    * ``"rsxdalv-faster"`` — rsxdalv fork ``faster`` branch with
      ``torch.compile`` + CUDA-graph optimisations for maximum speed.

    All three use the same ``chatterbox`` Python API.  The *package*
    installed is different for ``rsxdalv-faster`` (git branch) vs. the
    other two (PyPI ``chatterbox-tts``).

    Install instructions (safe — will NOT touch your existing torch/CUDA):

    **Official original / turbo:**
    ``pip install --no-deps chatterbox-tts``

    **rsxdalv faster branch:**
    ``pip install --no-deps git+https://github.com/rsxdalv/chatterbox.git@faster``

    Then install only the missing *non-torch* deps manually::

        pip install transformers accelerate tqdm scipy conformer

    See ``assistant_config.yml`` for full config examples.
    """

    # Chatterbox outputs 24 kHz audio.
    SAMPLE_RATE = 24000

    def __init__(
        self,
        voice: str | None = None,
        *,
        voice_file: str | None = None,
        model_type: str = "original",
        device: str = "auto",
        exaggeration: float = 0.5,
        cfg_weight: float = 0.5,
        **kwargs: Any,
    ) -> None:
        super().__init__(voice, **kwargs)
        self.voice_file = voice_file
        self.model_type = model_type.lower()
        self.device_preference = device.lower()
        self.exaggeration = exaggeration
        self.cfg_weight = cfg_weight
        self._model: Any = None
        self._resolved_device: str | None = None

        if self.model_type not in _CHATTERBOX_MODEL_TYPES:
            raise ValueError(
                f"Unknown Chatterbox model_type: {self.model_type!r}. "
                f"Available: {', '.join(sorted(_CHATTERBOX_MODEL_TYPES))}"
            )

    # -- Validation (R-21) --------------------------------------------------

    def _validate_voice_file(self) -> pathlib.Path:
        """Validate the voice reference WAV file exists and is usable."""
        if not self.voice_file:
            raise ValueError(
                "Chatterbox requires a voice_file path to a .wav reference file. "
                "Set tts.voice_file in assistant_config.yml."
            )
        path = pathlib.Path(self.voice_file)
        if not path.exists():
            raise FileNotFoundError(
                f"Chatterbox voice file not found: {path}"
            )
        if path.suffix.lower() != ".wav":
            raise ValueError(
                f"Chatterbox voice file must be a .wav file, got: {path.suffix!r}"
            )
        if path.stat().st_size == 0:
            raise ValueError(f"Chatterbox voice file is empty: {path}")
        return path

    # -- Model loading (R-20 lazy import) -----------------------------------

    def _resolve_device(self) -> str:
        if self._resolved_device is not None:
            return self._resolved_device
        if self.device_preference == "auto":
            try:
                import torch
                self._resolved_device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                self._resolved_device = "cpu"
        else:
            self._resolved_device = self.device_preference
        return self._resolved_device

    def _load_model(self) -> Any:
        """Lazy-load the Chatterbox model on first use (R-20)."""
        if self._model is not None:
            return self._model

        device = self._resolve_device()

        try:
            if self.model_type == "turbo":
                from chatterbox.tts import ChatterboxTurbo
                self._model = ChatterboxTurbo.from_pretrained(device=device)
            else:
                # Both "original" and "rsxdalv-faster" use the same class.
                # The rsxdalv-faster branch ships its optimisations inside
                # the same ChatterboxTTS2 class (torch.compile + CUDA graphs
                # are applied transparently).
                from chatterbox.tts import ChatterboxTTS2
                self._model = ChatterboxTTS2.from_pretrained(device=device)
        except ImportError as exc:
            if self.model_type == "rsxdalv-faster":
                install_cmd = (
                    "pip install --no-deps "
                    "git+https://github.com/rsxdalv/chatterbox.git@faster"
                )
            else:
                install_cmd = "pip install --no-deps chatterbox-tts"
            raise RuntimeError(
                f"chatterbox-tts package not installed. Run: {install_cmd}"
            ) from exc

        return self._model

    # -- Audio generation (R-18, R-22) --------------------------------------

    def stream_tts(self, text: str) -> Iterator[tuple[int, Any]]:
        """Generate voice-cloned audio for *text*.

        Long inputs are split at sentence boundaries (R-22) to prevent
        voice drift.  Each chunk yields a ``(sample_rate, audio_array)``
        tuple.
        """
        import numpy as np

        voice_path = self._validate_voice_file()
        model = self._load_model()

        chunks = _chunk_text(text)
        for chunk in chunks:
            if self.model_type == "turbo":
                wav = model.generate(chunk, audio_prompt_path=str(voice_path))
            else:
                wav = model.generate(
                    chunk,
                    audio_prompt_path=str(voice_path),
                    exaggeration=self.exaggeration,
                    cfg_weight=self.cfg_weight,
                )

            # Chatterbox returns a torch.Tensor — convert to numpy.
            if hasattr(wav, "numpy"):
                audio = wav.squeeze().cpu().numpy().astype(np.float32)
            else:
                audio = np.asarray(wav, dtype=np.float32)

            yield (self.SAMPLE_RATE, audio)


# ---------------------------------------------------------------------------
# Provider registry & factory
# ---------------------------------------------------------------------------

_PROVIDERS: dict[str, type[TTSBackend]] = {
    "kokoro": KokoroTTS,
    "pyttsx3": Pyttsx3TTS,
    "realtimetts": RealtimeTTSBackend,
    "chatterbox": ChatterboxTTS,
}


def get_tts_backend(config: ConfigNode) -> TTSBackend:
    """Instantiate the TTS backend specified in the config.

    Reads ``config.tts.provider`` and ``config.tts.voice`` to select and
    configure the appropriate backend.  Kokoro is the default.
    """
    provider = getattr(config.tts, "provider", "kokoro").lower()
    voice = getattr(config.tts, "voice", None)

    cls = _PROVIDERS.get(provider)
    if cls is None:
        raise ValueError(
            f"Unknown TTS provider: {provider!r}. "
            f"Available: {', '.join(sorted(_PROVIDERS))}"
        )

    kwargs: dict[str, Any] = {}
    # Forward any extra tts config keys (e.g. rate)
    tts_data = config.tts.to_dict()
    for key, value in tts_data.items():
        if key not in ("provider", "voice"):
            kwargs[key] = value

    return cls(voice=voice, **kwargs)
