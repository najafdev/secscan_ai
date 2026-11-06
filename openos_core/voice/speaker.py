"""
OpenOS Text-to-Speech Speaker.

Converts text responses to natural-sounding speech using:
  - edge-tts (Microsoft Edge TTS — free, high quality, async)
  - piper (fully offline, fast)
  - System espeak (basic fallback)
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

# Premium Edge TTS voices
VOICES = {
    "en": "en-US-GuyNeural",           # Male, natural
    "en-female": "en-US-JennyNeural",   # Female, natural
    "en-uk": "en-GB-RyanNeural",        # British male
    "en-au": "en-AU-NatashaNeural",     # Australian female
    "es": "es-ES-AlvaroNeural",
    "fr": "fr-FR-HenriNeural",
    "de": "de-DE-ConradNeural",
    "hi": "hi-IN-MadhurNeural",
    "ja": "ja-JP-KeitaNeural",
    "zh": "zh-CN-YunxiNeural",
    "ar": "ar-SA-HamedNeural",
    "pt": "pt-BR-AntonioNeural",
}

# OpenOS personality voice settings
OPENOS_VOICE = "en-US-GuyNeural"
OPENOS_RATE = "+5%"
OPENOS_PITCH = "+0Hz"


class Speaker:
    """Convert text to speech and play it."""

    def __init__(
        self,
        voice: str = OPENOS_VOICE,
        rate: str = OPENOS_RATE,
        pitch: str = OPENOS_PITCH,
        language: str = "en",
        backend: str = "auto",
    ):
        """
        Args:
            voice: Edge TTS voice name
            rate: Speech rate adjustment (e.g., '+10%', '-5%')
            pitch: Pitch adjustment (e.g., '+5Hz', '-2Hz')
            language: Language code
            backend: 'edge-tts', 'piper', 'espeak', or 'auto'
        """
        self._voice = voice or VOICES.get(language, OPENOS_VOICE)
        self._rate = rate
        self._pitch = pitch
        self._language = language
        self._backend = self._detect_backend() if backend == "auto" else backend

    def _detect_backend(self) -> str:
        """Auto-detect best available TTS backend."""
        try:
            import edge_tts
            return "edge-tts"
        except ImportError:
            pass

        if shutil.which("piper"):
            return "piper"

        if shutil.which("espeak-ng") or shutil.which("espeak"):
            return "espeak"

        return "none"

    def speak(self, text: str) -> bool:
        """
        Convert text to speech and play it.

        Returns True if speech was played successfully.
        """
        if not text or not text.strip():
            return False

        # Clean up text for speech (remove markdown, emojis, etc.)
        clean = self._clean_for_speech(text)
        if not clean:
            return False

        logger.info(f"Speaking ({self._backend}): '{clean[:80]}...'")

        if self._backend == "edge-tts":
            return self._speak_edge_tts(clean)
        elif self._backend == "piper":
            return self._speak_piper(clean)
        elif self._backend == "espeak":
            return self._speak_espeak(clean)
        else:
            logger.warning("No TTS backend available")
            return False

    def _clean_for_speech(self, text: str) -> str:
        """Clean text for natural speech output."""
        import re

        # Remove markdown formatting
        clean = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # **bold**
        clean = re.sub(r'\*(.*?)\*', r'\1', clean)      # *italic*
        clean = re.sub(r'`(.*?)`', r'\1', clean)        # `code`
        clean = re.sub(r'#{1,6}\s+', '', clean)         # ## headers
        clean = re.sub(r'[-•]\s+', '', clean)            # bullet points
        clean = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', clean)  # [links](url)

        # Remove common emoji (keep the text meaningful)
        clean = re.sub(r'[🔊📶🔋⚡🧠👋✅❌⚠️📸👁️📄🖥️💡🚀📥📦🎵🌐]', '', clean)

        # Collapse whitespace
        clean = re.sub(r'\n{2,}', '. ', clean)
        clean = re.sub(r'\n', ' ', clean)
        clean = re.sub(r'\s{2,}', ' ', clean)

        return clean.strip()

    def _speak_edge_tts(self, text: str) -> bool:
        """Speak using Microsoft Edge TTS (high quality, async)."""
        try:
            import edge_tts

            async def _generate_and_play():
                communicate = edge_tts.Communicate(
                    text=text,
                    voice=self._voice,
                    rate=self._rate,
                    pitch=self._pitch,
                )

                # Generate to temp file
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                    tmp_path = f.name

                try:
                    await communicate.save(tmp_path)
                    self._play_audio_file(tmp_path)
                finally:
                    Path(tmp_path).unlink(missing_ok=True)

            # Run async in sync context
            try:
                loop = asyncio.get_running_loop()
                # If already in an event loop, use a thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    loop.run_in_executor(pool, lambda: asyncio.run(_generate_and_play()))
            except RuntimeError:
                asyncio.run(_generate_and_play())

            return True
        except Exception as e:
            logger.error(f"Edge TTS failed: {e}")
            # Fallback to espeak
            return self._speak_espeak(text)

    def _speak_piper(self, text: str) -> bool:
        """Speak using Piper TTS (fully offline)."""
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                tmp_path = f.name

            result = subprocess.run(
                ["piper", "--output_file", tmp_path],
                input=text,
                text=True,
                capture_output=True,
                timeout=30,
            )

            if result.returncode == 0:
                self._play_audio_file(tmp_path)
                return True
            else:
                logger.error(f"Piper failed: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Piper TTS failed: {e}")
            return False
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def _speak_espeak(self, text: str) -> bool:
        """Speak using espeak-ng (basic but always available)."""
        try:
            cmd = "espeak-ng" if shutil.which("espeak-ng") else "espeak"
            if not shutil.which(cmd):
                logger.warning("No espeak found")
                return False

            subprocess.run(
                [cmd, "-v", self._language, "-s", "160", "-p", "50", text],
                capture_output=True,
                timeout=30,
            )
            return True
        except Exception as e:
            logger.error(f"espeak failed: {e}")
            return False

    def _play_audio_file(self, filepath: str) -> None:
        """Play an audio file using the best available player."""
        players = [
            (["mpv", "--no-terminal", "--no-video"], "mpv"),
            (["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"], "ffplay"),
            (["aplay"], "aplay"),
            (["paplay"], "paplay"),
        ]

        for cmd, name in players:
            if shutil.which(name):
                try:
                    subprocess.run(
                        cmd + [filepath],
                        capture_output=True,
                        timeout=120,
                    )
                    return
                except Exception:
                    continue

        # Last resort: sounddevice
        try:
            import sounddevice as sd
            import soundfile as sf
            data, sr = sf.read(filepath)
            sd.play(data, sr)
            sd.wait()
        except Exception as e:
            logger.error(f"Could not play audio: {e}")

    def set_voice(self, voice: str) -> None:
        """Change the TTS voice."""
        self._voice = voice

    def set_language(self, language: str) -> None:
        """Change language and auto-select voice."""
        self._language = language
        self._voice = VOICES.get(language, OPENOS_VOICE)

    @staticmethod
    def list_voices() -> dict[str, str]:
        """List available built-in voices."""
        return dict(VOICES)
