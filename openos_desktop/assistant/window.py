"""
OpenOS AI Assistant Window.

Floating ChatGPT-style assistant panel with conversation history,
triggered by Super+A keyboard shortcut.
"""

from __future__ import annotations

import asyncio
import threading

try:
    import gi
    gi.require_version("Gtk", "4.0")
    from gi.repository import Gdk, GLib, Gtk, Pango
    HAS_GTK = True
except (ImportError, ValueError):
    HAS_GTK = False


class AssistantWindow:
    """Floating AI assistant with chat interface."""

    def __init__(self):
        if not HAS_GTK:
            raise RuntimeError("GTK4 not available")

        self._brain = None
        self.window = Gtk.Window(title="OpenOS Assistant")
        self.window.set_default_size(420, 600)
        self.window.set_decorated(True)
        self.window.set_resizable(True)

        self._apply_css()
        self._build_ui()

    def _apply_css(self) -> None:
        css = b"""
        .assistant-window {
            background: #0a0e27;
        }
        .assistant-header {
            background: linear-gradient(90deg, #0a0e27, #1a1040);
            padding: 12px 16px;
            border-bottom: 1px solid rgba(124, 58, 237, 0.3);
        }
        .assistant-title {
            color: #00d4ff;
            font-size: 16px;
            font-weight: bold;
        }
        .assistant-subtitle {
            color: #666;
            font-size: 11px;
        }
        .chat-scroll {
            background: #0a0e27;
        }
        .chat-area {
            background: #0a0e27;
            padding: 12px;
        }
        .msg-user {
            background: rgba(0, 212, 255, 0.15);
            border-radius: 12px 12px 4px 12px;
            padding: 10px 14px;
            margin: 4px 0 4px 60px;
            color: #e0e0e0;
            font-size: 13px;
        }
        .msg-openos {
            background: rgba(124, 58, 237, 0.15);
            border-radius: 12px 12px 12px 4px;
            padding: 10px 14px;
            margin: 4px 60px 4px 0;
            color: #e0e0e0;
            font-size: 13px;
        }
        .input-area {
            background: rgba(255, 255, 255, 0.05);
            border-top: 1px solid rgba(0, 212, 255, 0.2);
            padding: 8px 12px;
        }
        .chat-input {
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(0, 212, 255, 0.3);
            border-radius: 20px;
            padding: 8px 16px;
            color: #ffffff;
            font-size: 13px;
        }
        .chat-input:focus {
            border-color: #00d4ff;
        }
        .send-btn {
            background: linear-gradient(135deg, #00d4ff, #7c3aed);
            border: none;
            border-radius: 20px;
            padding: 8px 16px;
            color: white;
            font-weight: bold;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _build_ui(self) -> None:
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main_box.add_css_class("assistant-window")
        self.window.set_child(main_box)

        # Header (Horizontal: Logo | Text Info)
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        header.add_css_class("assistant-header")

        # Logo image
        from pathlib import Path
        logo_path = Path(__file__).parents[2] / "public" / "logo.png"
        if logo_path.exists():
            logo_img = Gtk.Image.new_from_file(str(logo_path))
            logo_img.set_pixel_size(32)
            header.append(logo_img)

        header_text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        title = Gtk.Label(label="OpenOS Assistant", xalign=0)
        title.add_css_class("assistant-title")
        subtitle = Gtk.Label(label="Ask me anything about your system", xalign=0)
        subtitle.add_css_class("assistant-subtitle")
        header_text.append(title)
        header_text.append(subtitle)
        header.append(header_text)
        main_box.append(header)

        # Chat area
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.add_css_class("chat-scroll")
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.chat_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.chat_box.add_css_class("chat-area")
        scroll.set_child(self.chat_box)
        main_box.append(scroll)
        self._scroll = scroll

        # Input area
        input_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        input_box.add_css_class("input-area")

        self.input_entry = Gtk.Entry()
        self.input_entry.set_placeholder_text("Type a message...")
        self.input_entry.add_css_class("chat-input")
        self.input_entry.set_hexpand(True)
        self.input_entry.connect("activate", self._on_send)
        input_box.append(self.input_entry)

        send_btn = Gtk.Button(label="Send")
        send_btn.add_css_class("send-btn")
        send_btn.connect("clicked", self._on_send)
        input_box.append(send_btn)

        main_box.append(input_box)

        # Welcome message
        self._add_message("openos", "👋 Hi! I'm OpenOS, your AI assistant. How can I help?")

    def _add_message(self, role: str, text: str) -> None:
        label = Gtk.Label(label=text, wrap=True, xalign=0)
        label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        label.set_max_width_chars(40)
        label.add_css_class(f"msg-{role}")
        self.chat_box.append(label)

        # Auto-scroll to bottom
        GLib.idle_add(self._scroll_to_bottom)

    def _scroll_to_bottom(self) -> bool:
        adj = self._scroll.get_vadjustment()
        adj.set_value(adj.get_upper())
        return False

    def _on_send(self, widget) -> None:
        text = self.input_entry.get_text().strip()
        if not text:
            return

        self._add_message("user", text)
        self.input_entry.set_text("")

        # Process in background
        threading.Thread(target=self._process_async, args=(text,), daemon=True).start()

    def _process_async(self, text: str) -> None:
        try:
            if self._brain is None:
                from openos_core.brain.engine import OpenOSBrain
                self._brain = OpenOSBrain()
                asyncio.run(self._brain.initialize())

            result = asyncio.run(self._brain.process(text))
            response = result.get("response", "I couldn't process that.")
        except Exception as e:
            response = f"Error: {e}"

        GLib.idle_add(self._add_message, "openos", response)

    def show(self) -> None:
        self.window.present()

    def toggle(self) -> None:
        if self.window.get_visible():
            self.window.hide()
        else:
            self.window.present()
