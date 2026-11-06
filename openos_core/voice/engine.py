"""
OpenOS Voice Engine.

Main orchestrator for the always-on voice interface.
Ties together: Wake Word → Record → Transcribe → AI Brain → Speak

Usage:
    openos-voice              # Start always-on voice mode
    openos-voice --push       # Push-to-talk mode (press Enter to talk)
    openos-voice --once       # Listen once, respond, and exit
"""

from __future__ import annotations

import asyncio
import logging
import sys
import threading
import time

import click

logger = logging.getLogger(__name__)


class VoiceEngine:
    """Always-on voice interface for OpenOS."""

    def __init__(self):
        self._running = False
        self._brain = None
        self._listener = None
        self._transcriber = None
        self._speaker = None
        self._processing = False

    async def initialize(self) -> bool:
        """Set up all voice components and the AI brain."""
        from openos_core.config import get_config
        config = get_config()

        # Initialize AI Brain
        from openos_core.brain.engine import OpenOSBrain
        self._brain = OpenOSBrain()
        ok = await self._brain.initialize()
        if not ok:
            logger.error("Failed to initialize AI brain")
            return False

        # Initialize Voice Listener
        from openos_core.voice.listener import VoiceListener
        self._listener = VoiceListener(
            wake_word=config.voice.wake_word,
            silence_threshold=config.voice.silence_threshold,
            listen_timeout=config.voice.listen_timeout,
        )

        # Initialize Transcriber
        from openos_core.voice.transcriber import Transcriber
        self._transcriber = Transcriber(
            backend="openai",
            host=config.llm.host,
            api_key=config.llm.api_key,
        )

        # Initialize Speaker
        from openos_core.voice.speaker import Speaker
        self._speaker = Speaker(
            language=config.voice.language,
        )

        logger.info("Voice engine initialized")
        return True

    async def run_always_on(self) -> None:
        """Run in always-on mode: listen → process → speak → repeat."""
        from openos_core.shell.formatter import console

        self._running = True
        console.print("\n  [bold cyan]🎙️  OpenOS Voice Mode — Always On[/]")
        console.print("  [dim]Listening... Speak to interact. Press Ctrl+C to stop.[/]\n")

        # Greet
        self._speaker.speak("OpenOS is listening. How can I help?")

        while self._running:
            try:
                # Wait for voice activity
                wake_event = threading.Event()
                self._listener._running = True

                def on_wake():
                    wake_event.set()
                    self._listener._running = False

                # Listen in a thread
                listen_thread = threading.Thread(
                    target=self._listener.listen_for_wake_word,
                    args=(on_wake,),
                    daemon=True,
                )
                listen_thread.start()
                wake_event.wait()

                if not self._running:
                    break

                # Play listening chime
                console.print("  [cyan]🎤 Listening...[/]")

                # Record speech
                self._listener._running = True
                audio = self._listener.record_speech()

                if not audio:
                    console.print("  [dim]No speech detected.[/]")
                    continue

                # Transcribe
                console.print("  [yellow]💭 Transcribing...[/]")
                text = self._transcriber.transcribe(audio)

                if not text:
                    console.print("  [dim]Couldn't understand. Try again.[/]")
                    self._speaker.speak("Sorry, I didn't catch that.")
                    continue

                console.print(f"  [green]You said:[/] {text}")

                # Process with AI Brain
                console.print("  [yellow]🧠 Thinking...[/]")
                result = await self._brain.process(text)
                response = result.get("response", "I'm not sure how to help with that.")

                console.print(f"  [cyan]OpenOS:[/] {response}")

                # Speak response
                self._speaker.speak(response)
                console.print()

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Voice loop error: {e}")
                time.sleep(1)

        self.shutdown()

    async def run_push_to_talk(self) -> None:
        """Run in push-to-talk mode: press Enter to start recording."""
        from openos_core.shell.formatter import console

        self._running = True
        console.print("\n  [bold cyan]🎙️  OpenOS Voice Mode — Push to Talk[/]")
        console.print("  [dim]Press Enter to speak. Type 'quit' to exit.[/]\n")

        self._speaker.speak("Push to talk mode active. Press enter when you want to speak.")

        while self._running:
            try:
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: input("  Press Enter to speak (or 'quit'): "),
                )

                if user_input.strip().lower() in ("quit", "exit", "q"):
                    break

                console.print("  [cyan]🎤 Recording... Speak now![/]")

                # Record
                self._listener._running = True
                audio = self._listener.record_speech()

                if not audio:
                    console.print("  [dim]No speech detected.[/]")
                    continue

                # Transcribe
                console.print("  [yellow]💭 Transcribing...[/]")
                text = self._transcriber.transcribe(audio)

                if not text:
                    console.print("  [dim]Couldn't understand.[/]")
                    self._speaker.speak("Sorry, I didn't catch that.")
                    continue

                console.print(f"  [green]You:[/] {text}")

                # Process
                console.print("  [yellow]🧠 Thinking...[/]")
                result = await self._brain.process(text)
                response = result.get("response", "I'm not sure how to help with that.")

                console.print(f"  [cyan]OpenOS:[/] {response}")
                self._speaker.speak(response)
                console.print()

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error: {e}")

        self.shutdown()

    async def run_once(self) -> None:
        """Listen once, process, speak, and exit."""
        from openos_core.shell.formatter import console

        console.print("  [cyan]🎤 Listening... Speak now![/]")

        self._listener._running = True
        audio = self._listener.record_speech()

        if not audio:
            console.print("  [dim]No speech detected.[/]")
            return

        console.print("  [yellow]💭 Transcribing...[/]")
        text = self._transcriber.transcribe(audio)

        if not text:
            console.print("  [dim]Couldn't understand.[/]")
            return

        console.print(f"  [green]You:[/] {text}")
        console.print("  [yellow]🧠 Thinking...[/]")

        result = await self._brain.process(text)
        response = result.get("response", "")

        console.print(f"  [cyan]OpenOS:[/] {response}")
        self._speaker.speak(response)

        self.shutdown()

    def shutdown(self) -> None:
        """Clean up all components."""
        self._running = False
        if self._listener:
            self._listener.stop()
        if self._brain:
            self._brain.shutdown()
        logger.info("Voice engine shut down")


# ─── CLI Entry Point ───


@click.command()
@click.option("--push", is_flag=True, help="Push-to-talk mode (press Enter to record)")
@click.option("--once", is_flag=True, help="Listen once and exit")
@click.option("--voice", default=None, help="TTS voice name (e.g., en-US-JennyNeural)")
@click.option("--language", "-l", default=None, help="Language code (en, es, fr, etc.)")
@click.version_option(version="0.1.0", prog_name="OpenOS Voice")
def main(push: bool, once: bool, voice: str | None, language: str | None) -> None:
    """OpenOS Voice Interface — Talk to your OS.

    \b
    Modes:
      openos-voice          Always-on (listens continuously)
      openos-voice --push   Push-to-talk (press Enter to speak)
      openos-voice --once   One-shot (listen once, respond, exit)
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(message)s",
    )

    from openos_core.config import get_config
    config = get_config()

    if language:
        config.voice.language = language
    if voice:
        pass  # Will be set in Speaker

    engine = VoiceEngine()

    async def run():
        ok = await engine.initialize()
        if not ok:
            click.echo("❌ Failed to initialize voice engine. Check your AI backend config.")
            sys.exit(1)

        if voice:
            engine._speaker.set_voice(voice)

        if once:
            await engine.run_once()
        elif push:
            await engine.run_push_to_talk()
        else:
            await engine.run_always_on()

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        click.echo("\n  Goodbye! 👋")
        engine.shutdown()


if __name__ == "__main__":
    main()
