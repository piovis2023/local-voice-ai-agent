"""TTS abstraction layer with multi-backend support (R-07).

Provides a common ``stream_tts(text) -> Iterator[audio_chunk]`` interface with
swappable providers.  Provider is selected via ``assistant_config.yml``.
"""

from __future__ import annotations

import abc
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
        import io
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

        # Save to a temporary in-memory WAV buffer
        buf = io.BytesIO()
        engine.save_to_file(text, buf.name if hasattr(buf, "name") else "/tmp/_pyttsx3_tts.wav")
        engine.runAndWait()

        # Read back the WAV file and yield as numpy array
        wav_path = "/tmp/_pyttsx3_tts.wav"
        try:
            with wave.open(wav_path, "rb") as wf:
                sample_rate = wf.getframerate()
                frames = wf.readframes(wf.getnframes())
                audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
                yield (sample_rate, audio)
        except FileNotFoundError:
            raise RuntimeError("pyttsx3 failed to generate audio output.")


class RealtimeTTSBackend(TTSBackend):
    """RealtimeTTS with SystemEngine provider.

    Uses the ``RealtimeTTS`` library's ``SystemEngine`` for streaming
    text-to-speech via the system's native TTS capabilities.
    """

    def __init__(self, voice: str | None = None, **kwargs: Any) -> None:
        super().__init__(voice, **kwargs)

    def stream_tts(self, text: str) -> Iterator[tuple[int, Any]]:
        import numpy as np
        from RealtimeTTS import SystemEngine, TextToAudioStream

        engine = SystemEngine()
        if self.voice:
            engine.set_voice(self.voice)

        stream = TextToAudioStream(engine)
        stream.feed(text)

        sample_rate = 22050
        audio_chunks: list[bytes] = []

        def on_audio_chunk(chunk: bytes) -> None:
            audio_chunks.append(chunk)

        stream.play(on_audio_chunk=on_audio_chunk, muted=True)

        if audio_chunks:
            raw = b"".join(audio_chunks)
            audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
            yield (sample_rate, audio)


# ---------------------------------------------------------------------------
# Provider registry & factory
# ---------------------------------------------------------------------------

_PROVIDERS: dict[str, type[TTSBackend]] = {
    "kokoro": KokoroTTS,
    "pyttsx3": Pyttsx3TTS,
    "realtimetts": RealtimeTTSBackend,
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
