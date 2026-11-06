"""
OpenOS Speech-to-Text Transcriber.

Converts recorded audio to text using:
  - OpenAI Whisper API (via proxy or direct)
  - Local faster-whisper / whisper.cpp (offline fallback)
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


class Transcriber:
    """Convert speech audio to text."""

    def __init__(self, backend: str = "openai", host: str = "", api_key: str = "", model: str = "whisper-1"):
        """
        Args:
            backend: 'openai' (API), 'local' (faster-whisper), or 'google'
            host: API endpoint for OpenAI-compatible Whisper
            api_key: API key (leave empty for local proxies)
            model: Whisper model name
        """
        self._backend = backend
        self._host = host
        self._api_key = api_key
        self._model = model
        self._local_model = None

    def transcribe(self, audio_bytes: bytes, language: str = "en") -> str:
        """
        Transcribe audio bytes to text.

        Args:
            audio_bytes: WAV audio data
            language: Language code (e.g., 'en', 'es', 'fr')

        Returns:
            Transcribed text, or empty string on failure.
        """
        if self._backend == "openai":
            return self._transcribe_openai(audio_bytes, language)
        elif self._backend == "local":
            return self._transcribe_local(audio_bytes, language)
        else:
            return self._transcribe_openai(audio_bytes, language)

    def _transcribe_openai(self, audio_bytes: bytes, language: str) -> str:
        """Transcribe using OpenAI Whisper API (or compatible proxy)."""
        try:
            from openai import OpenAI

            key = self._api_key or "sk-local-proxy"
            base_url = self._host.rstrip("/") if self._host else "http://localhost:4141"
            if not base_url.endswith("/v1"):
                base_url = f"{base_url}/v1"

            client = OpenAI(base_url=base_url, api_key=key)

            # Write to temp file (API requires a file)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_bytes)
                tmp_path = f.name

            try:
                with open(tmp_path, "rb") as audio_file:
                    response = client.audio.transcriptions.create(
                        model=self._model,
                        file=audio_file,
                        language=language,
                        response_format="text",
                    )
                text = response.strip() if isinstance(response, str) else response.text.strip()
                logger.info(f"Transcribed ({self._backend}): '{text}'")
                return text
            finally:
                Path(tmp_path).unlink(missing_ok=True)

        except Exception as e:
            logger.error(f"OpenAI Whisper transcription failed: {e}")
            # Fallback to local
            return self._transcribe_local(audio_bytes, language)

    def _transcribe_local(self, audio_bytes: bytes, language: str) -> str:
        """Transcribe using local faster-whisper model."""
        try:
            from faster_whisper import WhisperModel

            if self._local_model is None:
                logger.info("Loading local Whisper model (first time may be slow)...")
                self._local_model = WhisperModel(
                    "base",
                    device="cpu",
                    compute_type="int8",
                )

            # Write WAV to temp
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio_bytes)
                tmp_path = f.name

            try:
                assert self._local_model is not None
                segments, info = self._local_model.transcribe(
                    tmp_path,
                    language=language,
                    beam_size=5,
                    vad_filter=True,
                )
                text = " ".join(seg.text for seg in segments).strip()
                logger.info(f"Transcribed (local): '{text}'")
                return text
            finally:
                Path(tmp_path).unlink(missing_ok=True)

        except ImportError:
            logger.error("faster-whisper not installed. pip install faster-whisper")
            return ""
        except Exception as e:
            logger.error(f"Local transcription failed: {e}")
            return ""
