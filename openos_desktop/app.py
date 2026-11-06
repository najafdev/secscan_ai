"""
OpenOS Desktop Shell — Main Application Entry Point.

Launches the complete OpenOS desktop environment: panel, launcher, assistant,
and notification daemon. Designed to run on top of a Wayfire/wlroots compositor.
"""

from __future__ import annotations

import asyncio
import logging
import sys
import threading

logger = logging.getLogger("openos-desktop")


def main() -> None:
    """Launch the OpenOS desktop shell."""
    try:
        import gi
        gi.require_version("Gtk", "4.0")
        from gi.repository import GLib, Gtk
    except (ImportError, ValueError):
        print("ERROR: GTK4 not available. Install: sudo apt install gir1.2-gtk-4.0 python3-gi")
        sys.exit(1)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")

    app = Gtk.Application(application_id="org.openos.desktop")

    def on_activate(application):
        logger.info("Starting OpenOS Desktop Shell...")

        # AI search callback
        def on_search(text: str):
            logger.info(f"Search: {text}")
            # Process through AI brain in background
            threading.Thread(
                target=_process_search,
                args=(text,),
                daemon=True,
            ).start()

        # Launch panel
        try:
            from openos_desktop.panel.panel import OpenOSPanel
            panel = OpenOSPanel(on_search_submit=on_search)
            panel.show()
            logger.info("Panel loaded.")
        except Exception as e:
            logger.error(f"Panel failed: {e}")

        # Launch assistant (hidden initially)
        try:
            from openos_desktop.assistant.window import AssistantWindow
            assistant = AssistantWindow()
            logger.info("Assistant ready (Super+A to open).")
        except Exception as e:
            logger.error(f"Assistant failed: {e}")

        # Launch dynamic widgets
        try:
            from openos_desktop.widgets import WidgetManager
            widget_manager = WidgetManager()
            widget_manager.start()
            logger.info("Dynamic Widgets started.")
        except Exception as e:
            logger.error(f"Widgets failed: {e}")

    app.connect("activate", on_activate)
    app.run(sys.argv)


def _process_search(text: str) -> None:
    """Process a search query through the AI brain."""
    try:
        from openos_core.brain.engine import OpenOSBrain
        brain = OpenOSBrain()
        asyncio.run(brain.initialize())
        result = asyncio.run(brain.process(text))
        logger.info(f"AI result: {result.get('response', '')[:100]}")
    except Exception as e:
        logger.error(f"Search processing failed: {e}")


if __name__ == "__main__":
    main()
