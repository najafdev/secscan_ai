"""
OpenOS Desktop Panel.

Top panel bar using GTK4 + gtk-layer-shell for Wayland compositors.
Contains: AI search bar, system tray indicators, clock.
"""

from __future__ import annotations

from datetime import datetime

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


class OpenOSPanel:
    """Top panel bar for OpenOS desktop."""

    def __init__(self, on_search_submit=None):
        if not HAS_GTK:
            raise RuntimeError("GTK4 not available. Install: apt install gir1.2-gtk-4.0")

        self.on_search_submit = on_search_submit
        self.window = Gtk.Window(title="OpenOS Panel")
        self.window.set_default_size(-1, 36)
        self.window.set_decorated(False)

        # Layer shell setup (for Wayland)
        if HAS_LAYER_SHELL:
            GtkLayerShell.init_for_window(self.window)
            GtkLayerShell.set_layer(self.window, GtkLayerShell.Layer.TOP)
            GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.TOP, True)
            GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.LEFT, True)
            GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.RIGHT, True)
            GtkLayerShell.set_exclusive_zone(self.window, 36)

        # Apply CSS
        self._apply_css()

        # Build panel layout
        self._build_ui()

        # Update clock every second
        GLib.timeout_add_seconds(1, self._update_clock)

    def _apply_css(self) -> None:
        css = b"""
        .openos-panel {
            background: linear-gradient(180deg, rgba(10, 14, 39, 0.95), rgba(10, 14, 39, 0.85));
            border-bottom: 1px solid rgba(0, 212, 255, 0.2);
            padding: 2px 12px;
        }
        .openos-panel label {
            color: #e0e0e0;
            font-family: 'Inter', 'Segoe UI', sans-serif;
            font-size: 13px;
        }
        .openos-brand {
            color: #00d4ff;
            font-weight: bold;
            font-size: 14px;
        }
        .openos-search {
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(0, 212, 255, 0.3);
            border-radius: 18px;
            padding: 4px 16px;
            color: #ffffff;
            font-size: 13px;
            min-width: 300px;
        }
        .openos-search:focus {
            border-color: #00d4ff;
            background: rgba(255, 255, 255, 0.12);
            box-shadow: 0 0 8px rgba(0, 212, 255, 0.3);
        }
        .openos-clock {
            color: #b0b0b0;
            font-size: 13px;
            font-variant-numeric: tabular-nums;
        }
        .openos-indicator {
            color: #7c3aed;
            font-size: 14px;
            padding: 0 6px;
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
        # Main horizontal box
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        hbox.add_css_class("openos-panel")
        self.window.set_child(hbox)

        # Brand container (Horizontal box for logo + text)
        brand_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        brand_box.add_css_class("openos-brand-box")

        from pathlib import Path
        logo_path = Path(__file__).parents[2] / "public" / "logo.png"
        if logo_path.exists():
            logo_img = Gtk.Image.new_from_file(str(logo_path))
            logo_img.set_pixel_size(18)
            brand_box.append(logo_img)

        brand = Gtk.Label(label="OpenOS")
        brand.add_css_class("openos-brand")
        brand_box.append(brand)
        hbox.append(brand_box)

        # Spacer
        spacer1 = Gtk.Box()
        spacer1.set_hexpand(True)
        hbox.append(spacer1)

        # AI Search bar (center)
        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text("Ask OpenOS anything...")
        self.search_entry.add_css_class("openos-search")
        self.search_entry.connect("activate", self._on_search_activate)
        hbox.append(self.search_entry)

        # Spacer
        spacer2 = Gtk.Box()
        spacer2.set_hexpand(True)
        hbox.append(spacer2)

        # System indicators
        indicators = ["🔊", "📶", "🔋"]
        for ind in indicators:
            lbl = Gtk.Label(label=ind)
            lbl.add_css_class("openos-indicator")
            hbox.append(lbl)

        # Clock
        self.clock_label = Gtk.Label()
        self.clock_label.add_css_class("openos-clock")
        self._update_clock()
        hbox.append(self.clock_label)

    def _update_clock(self) -> bool:
        now = datetime.now().strftime("%H:%M  %b %d")
        self.clock_label.set_text(now)
        return True  # Keep timer running

    def _on_search_activate(self, entry: Gtk.Entry) -> None:
        text = entry.get_text().strip()
        if text and self.on_search_submit:
            self.on_search_submit(text)
        entry.set_text("")

    def show(self) -> None:
        self.window.present()
