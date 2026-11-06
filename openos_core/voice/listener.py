"""
OpenOS Voice Listener.

Handles microphone input, wake word detection, and voice recording.
Supports multiple wake word backends:
  - Picovoice Porcupine (requires free API key)
  - Simple energy-based detection (no dependencies)
  - Manual push-to-talk mode
"""

from __future__ import annotations

import io
import logging
import struct
import time
import wave
from typing import Callable

import numpy as np

logger = logging.getLogger(__name__)

# Audio constants
SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "int16"
FRAME_DURATION_MS = 30
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)


class VoiceListener:
    """Microphone listener with wake word detection."""

    def __init__(
        self,
        wake_word: str = "hey openos",
        porcupine_key: str = "",
        silence_threshold: float = 0.03,
        listen_timeout: int = 10,
        max_record_seconds: int = 30,
    ):
        self.wake_word = wake_word
        self._porcupine_key = porcupine_key
        self._silence_threshold = silence_threshold
        self._listen_timeout = listen_timeout
        self._max_record_seconds = max_record_seconds
        self._running = False
        self._porcupine = None

        # Try to initialize Porcupine
        if porcupine_key:
            self._init_porcupine()

    def _init_porcupine(self) -> None:
        """Initialize Picovoice Porcupine wake word engine."""
        try:
            import pvporcupine
            self._porcupine = pvporcupine.create(
                access_key=self._porcupine_key,
                keywords=["hey siri"],  # closest built-in; custom keyword needs training
            )
            logger.info("Porcupine wake word engine initialized")
        except ImportError:
            logger.warning("pvporcupine not installed. Using energy-based detection.")
        except Exception as e:
            logger.warning(f"Porcupine init failed: {e}. Using energy-based detection.")

    def listen_for_wake_word(self, on_wake: Callable[[], None]) -> None:
        """
        Block and listen for the wake word. Calls on_wake() when detected.

        Falls back to energy-based detection if Porcupine isn't available.
        """

        self._running = True
        logger.info(f"Listening for wake word: '{self.wake_word}'...")

        if self._porcupine:
            self._listen_porcupine(on_wake)
        else:
            self._listen_energy(on_wake)

    def _listen_porcupine(self, on_wake: Callable[[], None]) -> None:
        """Listen using Porcupine wake word engine."""
        import sounddevice as sd

        assert self._porcupine is not None
        frame_length = self._porcupine.frame_length

        def audio_callback(indata, frames, time_info, status):
            if not self._running:
                raise sd.CallbackStop()
            pcm = struct.unpack_from(f"{frame_length}h", indata.tobytes())
            result = self._porcupine.process(pcm)
            if result >= 0:
                logger.info("Wake word detected (Porcupine)!")
                on_wake()

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=frame_length,
            callback=audio_callback,
        ):
            while self._running:
                time.sleep(0.1)

    def _listen_energy(self, on_wake: Callable[[], None]) -> None:
        """
        Simple energy-based voice activity detection.

        Detects when someone starts speaking loudly (above threshold).
        This is a simple fallback when no wake word engine is available.
        """
        import sounddevice as sd

        # Detect any speech above the energy threshold
        silence_count = 0
        triggered = False

        def audio_callback(indata, frames, time_info, status):
            nonlocal silence_count, triggered
            if not self._running:
                raise sd.CallbackStop()

            # Calculate RMS energy
            audio = indata.flatten().astype(np.float32) / 32768.0
            rms = np.sqrt(np.mean(audio ** 2))

            if rms > self._silence_threshold:
                if not triggered:
                    triggered = True
                    silence_count = 0
                    logger.info("Voice activity detected!")
                    on_wake()
            else:
                if triggered:
                    silence_count += 1
                    # Reset after ~2 seconds of silence
                    if silence_count > int(2000 / FRAME_DURATION_MS):
                        triggered = False
                        silence_count = 0

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=FRAME_SIZE,
            callback=audio_callback,
        ):
            while self._running:
                time.sleep(0.1)

    def record_speech(self) -> bytes | None:
        """
        Record speech until silence is detected.

        Returns WAV audio bytes, or None if nothing was recorded.
        """
        import sounddevice as sd

        logger.info("Recording speech...")
        frames: list[np.ndarray] = []
        silence_frames = 0
        has_speech = False
        max_frames = int(self._max_record_seconds * SAMPLE_RATE / FRAME_SIZE)
        silence_limit = int(1500 / FRAME_DURATION_MS)  # 1.5s of silence = end

        try:
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                dtype=DTYPE,
                blocksize=FRAME_SIZE,
            ) as stream:
                for _ in range(max_frames):
                    if not self._running:
                        break

                    data, _ = stream.read(FRAME_SIZE)
                    frames.append(data.copy())

                    # Check energy
                    audio = data.flatten().astype(np.float32) / 32768.0
                    rms = np.sqrt(np.mean(audio ** 2))

                    if rms > self._silence_threshold:
                        has_speech = True
                        silence_frames = 0
                    else:
                        silence_frames += 1

                    # End on sustained silence (only if we've heard speech)
                    if has_speech and silence_frames > silence_limit:
                        logger.info("Silence detected, stopping recording.")
                        break

        except Exception as e:
            logger.error(f"Recording error: {e}")
            return None

        if not has_speech or not frames:
            logger.info("No speech detected.")
            return None

        # Convert to WAV bytes
        audio_data = np.concatenate(frames)
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio_data.tobytes())

        wav_bytes = wav_buffer.getvalue()
        duration = len(audio_data) / SAMPLE_RATE
        logger.info(f"Recorded {duration:.1f}s of audio ({len(wav_bytes)} bytes)")
        return wav_bytes

    def stop(self) -> None:
        """Stop listening."""
        self._running = False
        if self._porcupine:
            try:
                self._porcupine.delete()
            except Exception:
                pass
