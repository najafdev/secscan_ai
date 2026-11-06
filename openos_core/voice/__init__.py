"""
OpenOS Voice Interface.

Always-on voice control for OpenOS:
  Wake Word → Record → Transcribe → AI Brain → Speak

Modules:
  listener.py    — Wake word detection & audio recording
  transcriber.py — Speech-to-text (Whisper API / local)
  speaker.py     — Text-to-speech (Edge TTS / Piper / espeak)
  engine.py      — Main voice orchestrator
"""

__version__ = "0.1.0"
