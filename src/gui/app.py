"""
Aplicación principal GTK4 / Libadwaita para G502 Profile Manager.
"""

from __future__ import annotations

import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, Gtk

from adapters.application_discovery_adapter import ApplicationDiscoveryAdapter
from adapters.ratbag_adapter import RatbagDeviceAdapter
from gui.window import MainWindow
from services.action_catalog import ActionCatalogService
from services.profile_manager import ProfileManager
from storage.profile_repository import JsonProfileRepository


class G502Application(Adw.Application):
    """
    Controlador de la aplicación de escritorio Libadwaita para el gestor de perfiles G502.
    """

    def __init__(self):
        super().__init__(
            application_id="io.github.thelion.G502ProfileManager",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self._window: MainWindow | None = None

    def do_startup(self):
        Adw.Application.do_startup(self)

        # Forzar tema oscuro moderno estilo Libadwaita / GNOME
        style_manager = Adw.StyleManager.get_default()
        style_manager.set_color_scheme(Adw.ColorScheme.PREFER_DARK)

        # Cargar estilos CSS personalizados
        css_path = Path(__file__).parent / "style.css"
        if css_path.exists():
            css_provider = Gtk.CssProvider()
            css_provider.load_from_path(str(css_path))
            display = Gdk.Display.get_default()
            if display:
                Gtk.StyleContext.add_provider_for_display(
                    display,
                    css_provider,
                    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
                )

    def do_activate(self):
        if not self._window:
            repository = JsonProfileRepository()
            profile_manager = ProfileManager(repository=repository)
            catalog_service = ActionCatalogService()
            discovery_adapter = ApplicationDiscoveryAdapter()
            ratbag_adapter = RatbagDeviceAdapter()

            self._window = MainWindow(
                app=self,
                profile_manager=profile_manager,
                catalog_service=catalog_service,
                discovery_adapter=discovery_adapter,
                ratbag_adapter=ratbag_adapter,
            )

        self._window.present()


def main():
    app = G502Application()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
