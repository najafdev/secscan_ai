"""
OpenOS Installer GUI Window.

A GTK4/Adwaita user interface providing a chat experience for OS installation.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk, Pango

from openos_installer.agent import InstallerAgent
from openos_installer.backend import InstallationBackend
from openos_installer.config import InstallConfig


class InstallerWindow(Gtk.ApplicationWindow):
    """Main window for the OpenOS graphical installer."""

    def __init__(self, app: Gtk.Application):
        super().__init__(application=app, title="OpenOS Installer")
        self.set_default_size(900, 600)

        # Load CSS
        css_provider = Gtk.CssProvider()
        css_path = Path(__file__).parent / "style.css"
        if css_path.exists():
            css_provider.load_from_path(str(css_path))
            Gtk.StyleContext.add_provider_for_display(
                self.get_display(),
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )

        # Installation State & Logic
        self.config = InstallConfig()
        self.agent = InstallerAgent(self.config)
        self.agent.set_callbacks(self._on_state_change, self._on_start_install)
        self.backend = InstallationBackend(self.config)

        # Build UI
        self._build_ui()

        # Initialize Agent async
        GLib.idle_add(self._init_agent)

    def _build_ui(self) -> None:
        """Construct the GTK widget tree."""
        # Main Layout (HBox: Sidebar | Main Area)
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.set_child(self.main_box)

        # ─── Sidebar (Checklist) ───
        self.sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.sidebar.add_css_class("sidebar")
        self.sidebar.set_size_request(250, -1)

        # Logo
        logo_path = Path(__file__).parent.parent / "public" / "logo.png"
        if logo_path.exists():
            logo_image = Gtk.Image.new_from_file(str(logo_path))
            logo_image.set_pixel_size(128)
            logo_image.set_halign(Gtk.Align.CENTER)
            logo_image.set_margin_bottom(20)
            self.sidebar.append(logo_image)

        title = Gtk.Label(label="Installation Setup")
        title.add_css_class("title")
        title.set_halign(Gtk.Align.START)
        self.sidebar.append(title)

        # Status labels
        self.status_labels = {}
        for key in ["Username", "Password", "Timezone", "Target Disk", "Hostname"]:
            lbl = Gtk.Label(label=f"{key}: ❌ Pending")
            lbl.set_halign(Gtk.Align.START)
            self.sidebar.append(lbl)
            self.status_labels[key] = lbl

        self.main_box.append(self.sidebar)

        # ─── Main Area (Chat + Input) ───
        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.content_box.set_hexpand(True)
        self.main_box.append(self.content_box)

        # Chat scroll view
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_vexpand(True)
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.content_box.append(self.scroll)

        # Chat message container
        self.chat_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.chat_box.set_margin_top(20)
        self.chat_box.set_margin_bottom(20)
        self.chat_box.set_margin_start(40)
        self.chat_box.set_margin_end(40)
        self.scroll.set_child(self.chat_box)

        # Input Area
        self.input_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.input_box.add_css_class("input-area")
        self.content_box.append(self.input_box)

        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text("Type your message here...")
        self.entry.set_hexpand(True)
        self.entry.connect("activate", self._on_send_clicked)
        self.input_box.append(self.entry)

        self.send_btn = Gtk.Button(label="➤")
        self.send_btn.add_css_class("send-btn")
        self.send_btn.connect("clicked", self._on_send_clicked)
        self.input_box.append(self.send_btn)

        # ─── Installation Progress Overlay ───
        self.progress_overlay = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.progress_overlay.add_css_class("progress-container")
        self.progress_overlay.set_valign(Gtk.Align.CENTER)
        self.progress_overlay.set_halign(Gtk.Align.CENTER)
        self.progress_overlay.set_size_request(400, -1)

        self.progress_label = Gtk.Label(label="Preparing installation...")
        self.progress_label.add_css_class("progress-label")
        self.progress_overlay.append(self.progress_label)

        self.progress_bar = Gtk.ProgressBar()
        self.progress_overlay.append(self.progress_bar)

    def _init_agent(self) -> bool:
        """Initialize the AI agent asynchronously without blocking GTK."""
        def run_init():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success = loop.run_until_complete(self.agent.initialize())
            GLib.idle_add(self._on_agent_initialized, success)

        import threading
        threading.Thread(target=run_init, daemon=True).start()
        return False  # Don't run this idle handler again

    def _on_agent_initialized(self, success: bool) -> None:
        if success:
            self._add_message("ai", "Hello! I'm OpenOS, your installation assistant. I'll guide you through setting up OpenOS. To get started, would you like me to list the available disks to install to?")
        else:
            self._add_message("ai", "⚠️ Failed to initialize AI Engine. Please check your configuration.")
            self.entry.set_sensitive(False)
            self.send_btn.set_sensitive(False)

    def _add_message(self, role: str, text: str) -> None:
        """Add a message bubble to the chat."""
        lbl = Gtk.Label(label=text)
        lbl.set_wrap(True)
        lbl.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        lbl.set_selectable(True)
        lbl.set_halign(Gtk.Align.END if role == "user" else Gtk.Align.START)
        lbl.add_css_class("chat-bubble")
        lbl.add_css_class(role)

        self.chat_box.append(lbl)

        # Scroll to bottom
        GLib.idle_add(self._scroll_to_bottom)

    def _scroll_to_bottom(self) -> bool:
        adj = self.scroll.get_vadjustment()
        adj.set_value(adj.get_upper() - adj.get_page_size())
        return False

    def _on_send_clicked(self, widget) -> None:
        """Handle user submitting a message."""
        text = self.entry.get_text().strip()
        if not text:
            return

        self.entry.set_text("")
        self.entry.set_sensitive(False)
        self.send_btn.set_sensitive(False)

        self._add_message("user", text)

        # Process via agent in background thread
        def run_agent():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            response = loop.run_until_complete(self.agent.process(text))
            GLib.idle_add(self._on_agent_response, response)

        import threading
        threading.Thread(target=run_agent, daemon=True).start()

    def _on_agent_response(self, response: str) -> None:
        """Handle the response coming back from the agent thread."""
        self._add_message("ai", response)
        self.entry.set_sensitive(True)
        self.send_btn.set_sensitive(True)
        self.entry.grab_focus()

    def _on_state_change(self) -> None:
        """Called by the InstallerTool when configuration is updated."""
        # Update sidebar labels
        summary = self.config.get_summary()
        for key, val in summary.items():
            if key in self.status_labels:
                GLib.idle_add(self.status_labels[key].set_text, f"{key}: {val}")

    def _on_start_install(self) -> None:
        """Called by the InstallerTool to begin the actual installation."""
        GLib.idle_add(self._show_progress_screen)

    def _show_progress_screen(self) -> None:
        """Hide chat and show the progress bar."""
        # Remove current children of main_box
        self.main_box.remove(self.sidebar)
        self.main_box.remove(self.content_box)

        # Add progress overlay centered
        center_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        center_box.set_hexpand(True)
        center_box.set_halign(Gtk.Align.CENTER)
        center_box.append(self.progress_overlay)

        self.main_box.append(center_box)

        # Start backend process in background thread
        def run_backend():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            def update_progress(pct, msg):
                GLib.idle_add(self._update_progress_ui, pct, msg)

            loop.run_until_complete(self.backend.run_installation(update_progress))
            GLib.idle_add(self._on_install_complete)

        import threading
        threading.Thread(target=run_backend, daemon=True).start()

    def _update_progress_ui(self, pct: float, msg: str) -> None:
        self.progress_bar.set_fraction(pct)
        self.progress_label.set_text(msg)

    def _on_install_complete(self) -> None:
        self.progress_label.set_text("✅ Installation Complete! You can reboot now.")

        btn = Gtk.Button(label="Reboot System")
        btn.add_css_class("send-btn")
        btn.set_margin_top(20)
        btn.connect("clicked", lambda x: self.close())
        self.progress_overlay.append(btn)
