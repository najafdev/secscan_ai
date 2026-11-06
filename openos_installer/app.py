"""
OpenOS Installer Entry Point.

Starts the GTK4 application.
"""

from __future__ import annotations

import sys

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, Gtk

from openos_installer.ui import InstallerWindow


class InstallerApplication(Gtk.Application):
    """Main Application wrapper."""

    def __init__(self):
        super().__init__(
            application_id="org.openos.Installer",
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = InstallerWindow(self)
        win.present()


def main() -> None:
    app = InstallerApplication()
    sys.exit(app.run(sys.argv))


if __name__ == "__main__":
    main()
