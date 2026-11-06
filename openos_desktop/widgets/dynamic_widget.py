"""
OpenOS Dynamic Desktop Widget (Conky alternative).

A Wayland-native background widget that adapts to user context.
"""

from __future__ import annotations

import logging
import subprocess
from datetime import datetime

import psutil

try:
    import gi
    gi.require_version("Gtk", "4.0")
    from gi.repository import Gdk, GLib, Gtk, Pango
    HAS_GTK = True
except (ImportError, ValueError):
    HAS_GTK = False

try:
    gi.require_version("GtkLayerShell", "0.1")
    from gi.repository import GtkLayerShell
    HAS_LAYER_SHELL = True
except (ImportError, ValueError, NameError):
    HAS_LAYER_SHELL = False

logger = logging.getLogger(__name__)


class DynamicWidget:
    """A dynamic, context-aware desktop widget."""

    def __init__(self):
        if not HAS_GTK:
            raise RuntimeError("GTK4 not available.")

        self.window = Gtk.Window(title="OpenOS Widget")
        self.window.set_decorated(False)

        # Layer shell setup (for Wayland) - pinned to bottom right
        if HAS_LAYER_SHELL:
            GtkLayerShell.init_for_window(self.window)
            GtkLayerShell.set_layer(self.window, GtkLayerShell.Layer.BOTTOM)
            GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.BOTTOM, True)
            GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.RIGHT, True)
            GtkLayerShell.set_margin(self.window, GtkLayerShell.Edge.BOTTOM, 40)
            GtkLayerShell.set_margin(self.window, GtkLayerShell.Edge.RIGHT, 40)
        else:
            self.window.set_default_size(250, 150)

        self._apply_css()

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.main_box.add_css_class("openos-widget-box")
        self.window.set_child(self.main_box)

        self.title_label = Gtk.Label()
        self.title_label.add_css_class("openos-widget-title")
        self.title_label.set_halign(Gtk.Align.START)

        self.content_label = Gtk.Label()
        self.content_label.add_css_class("openos-widget-content")
        self.content_label.set_halign(Gtk.Align.START)
        self.content_label.set_use_markup(True)

        self.main_box.append(self.title_label)
        self.main_box.append(self.content_label)

        self.current_state = "idle"
        self._update_timer_id = None
        self.set_state("idle")

    def _apply_css(self) -> None:
        css = b"""
        .openos-widget-box {
            background: rgba(10, 14, 39, 0.4);
            border: 1px solid rgba(0, 212, 255, 0.2);
            border-radius: 12px;
            padding: 16px;
            min-width: 200px;
        }
        .openos-widget-title {
            color: #00d4ff;
            font-family: 'Inter', 'Segoe UI', sans-serif;
            font-size: 14px;
            font-weight: bold;
            margin-bottom: 4px;
        }
        .openos-widget-content {
            color: #e0e0e0;
            font-family: 'Inter', 'Segoe UI', sans-serif;
            font-size: 13px;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def set_state(self, state: str) -> None:
        """Change the current widget state (idle, coding, gaming)."""
        logger.info(f"Widget state changing to: {state}")
        self.current_state = state
        self.update_content()

        if self._update_timer_id is not None:
            GLib.source_remove(self._update_timer_id)
            self._update_timer_id = None

        # Update every second for dynamic content
        self._update_timer_id = GLib.timeout_add_seconds(1, self.update_content)

    def update_content(self) -> bool:
        """Update the widget content based on current state."""
        try:
            if self.current_state == "coding":
                self._render_coding()
            elif self.current_state == "gaming":
                self._render_gaming()
            else:
                self._render_idle()
        except Exception as e:
            logger.error(f"Failed to update widget content: {e}")
            self.title_label.set_text("System Monitor")
            self.content_label.set_text("Error loading data.")

        return True  # Keep timer running

    def _render_idle(self) -> None:
        self.title_label.set_text("⚡ System Idle")
        now = datetime.now().strftime("%A, %B %d\n%H:%M:%S")

        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent

        markup = f"<b>Time:</b>\n{now}\n\n<b>CPU:</b> {cpu}%\n<b>RAM:</b> {mem}%"
        self.content_label.set_markup(markup)

    def _render_coding(self) -> None:
        self.title_label.set_text("👨‍💻 Coding Mode")

        # Get git status for ~/openos
        target_dir = "/home/kali/openos"

        try:
            # Check branch
            branch_out = subprocess.check_output(
                ["git", "branch", "--show-current"],
                cwd=target_dir, stderr=subprocess.DEVNULL, text=True
            ).strip()

            # Check if dirty
            status_out = subprocess.check_output(
                ["git", "status", "--porcelain"],
                cwd=target_dir, stderr=subprocess.DEVNULL, text=True
            )
            is_dirty = len(status_out) > 0
            dirty_str = " (Uncommitted changes)" if is_dirty else " (Clean)"

            markup = f"<b>Project:</b> openos\n<b>Branch:</b> {branch_out}{dirty_str}"
        except Exception:
            markup = "<b>Project:</b> Unknown\n<i>Not a git repository</i>"

        self.content_label.set_markup(markup)

    def _render_gaming(self) -> None:
        self.title_label.set_text("🎮 Gaming Mode")

        # Fetch temperatures
        temp_markup = ""
        try:
            temps = psutil.sensors_temperatures()
            if not temps:
                temp_markup = "Sensors unavailable."
            else:
                lines = []
                for name, entries in temps.items():
                    for entry in entries:
                        lines.append(f"<b>{name} ({entry.label or 'Core'}):</b> {entry.current}°C")
                temp_markup = "\n".join(lines[:4]) # Show up to 4 sensors
        except Exception:
            temp_markup = "Failed to read sensors."

        self.content_label.set_markup(temp_markup)

    def show(self) -> None:
        self.window.present()
