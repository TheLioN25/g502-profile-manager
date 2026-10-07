"""
Pruebas unitarias para TrayIndicator (System Tray / StatusNotifierItem).
"""

from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

src_path = Path(__file__).resolve().parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from gui.tray import TrayIndicator


class TestGuiTray(unittest.TestCase):
    def setUp(self):
        from i18n import set_language
        set_language("es", persist=False)

    @patch("gi.repository.Gio.bus_get_sync")
    def test_tray_initialization_and_registration(self, mock_bus_get):
        mock_bus = MagicMock()
        mock_bus.register_object.return_value = 42
        mock_bus_get.return_value = mock_bus

        tray = TrayIndicator()
        self.assertTrue(tray.is_available)
        mock_bus.register_object.assert_called_once()
        mock_bus.call_sync.assert_called_once()
        self.assertEqual(mock_bus.call_sync.call_args[0][0], "org.kde.StatusNotifierWatcher")

    @patch("gi.repository.Gio.bus_get_sync")
    def test_tray_graceful_fallback_when_dbus_fails(self, mock_bus_get):
        mock_bus_get.side_effect = RuntimeError("D-Bus no disponible")

        tray = TrayIndicator()
        self.assertFalse(tray.is_available)

    @patch("gi.repository.Gio.bus_get_sync")
    def test_tray_properties_and_tooltip_update(self, mock_bus_get):
        mock_bus = MagicMock()
        mock_bus.register_object.return_value = 42
        mock_bus_get.return_value = mock_bus

        tray = TrayIndicator()
        tray.update_status(
            profile_name="Warframe Live",
            app_name="Warframe",
            dpi=8000,
            auto_active=True,
        )

        mock_bus.emit_signal.assert_called_with(
            None,
            tray._object_path,
            "org.kde.StatusNotifierItem",
            "NewToolTip",
            None,
        )

        # Probar lectura de propiedades
        id_val = tray._handle_get_property(mock_bus, "caller", "/StatusNotifierItem", "org.kde.StatusNotifierItem", "Id")
        self.assertEqual(id_val.unpack(), "io.github.thelion.G502ProfileManager")

        tooltip_val = tray._handle_get_property(mock_bus, "caller", "/StatusNotifierItem", "org.kde.StatusNotifierItem", "ToolTip")
        unpacked_tooltip = tooltip_val.unpack()
        self.assertIn("Warframe Live", unpacked_tooltip[2])
        self.assertIn("8000 DPI", unpacked_tooltip[3])
        self.assertIn("Auto: Activo", unpacked_tooltip[3])

        # Probar con nivel de batería incluido
        tray.update_status(
            profile_name="Lightspeed Game",
            app_name="Warframe",
            dpi=1600,
            auto_active=True,
            battery_level=85,
        )
        tooltip_with_bat = tray._handle_get_property(mock_bus, "caller", "/StatusNotifierItem", "org.kde.StatusNotifierItem", "ToolTip")
        unpacked_bat = tooltip_with_bat.unpack()
        self.assertIn("🔋 85%", unpacked_bat[3])

    @patch("gi.repository.Gio.bus_get_sync")
    def test_tray_method_calls_and_callbacks(self, mock_bus_get):
        mock_bus = MagicMock()
        mock_bus.register_object.return_value = 42
        mock_bus_get.return_value = mock_bus

        activate_called = []
        toggle_auto_called = []

        tray = TrayIndicator(
            on_activate=lambda: activate_called.append(True),
            on_toggle_auto=lambda: toggle_auto_called.append(True),
        )

        invocation = MagicMock()
        with patch("gi.repository.GLib.idle_add", side_effect=lambda fn, *args: fn(*args)):
            tray._handle_method_call(
                mock_bus, "caller", "/StatusNotifierItem", "org.kde.StatusNotifierItem",
                "Activate", MagicMock(), invocation
            )
            self.assertEqual(len(activate_called), 1)

            tray._handle_method_call(
                mock_bus, "caller", "/StatusNotifierItem", "org.kde.StatusNotifierItem",
                "SecondaryActivate", MagicMock(), invocation
            )
            self.assertEqual(len(toggle_auto_called), 1)

    @patch("gi.repository.Gio.bus_get_sync")
    def test_tray_destroy_unregisters_cleanly(self, mock_bus_get):
        mock_bus = MagicMock()
        mock_bus.register_object.return_value = 42
        mock_bus_get.return_value = mock_bus

        tray = TrayIndicator()
        self.assertTrue(tray.is_available)
        tray.destroy()
        mock_bus.unregister_object.assert_called_once_with(42)
        self.assertFalse(tray.is_available)



    @patch("gi.repository.Gio.bus_get_sync")
    def test_tray_tooltip_respects_i18n_language(self, mock_bus_get):
        from i18n import set_language
        mock_bus = MagicMock()
        mock_bus.register_object.return_value = 42
        mock_bus_get.return_value = mock_bus

        tray = TrayIndicator()
        tray.update_status("Game", "App", dpi=2400, auto_active=True)

        set_language("en", persist=False)
        try:
            tooltip_val = tray._handle_get_property(mock_bus, "caller", "/StatusNotifierItem", "org.kde.StatusNotifierItem", "ToolTip")
            unpacked = tooltip_val.unpack()
            self.assertIn("Auto: Active", unpacked[3])
        finally:
            set_language("es", persist=False)

if __name__ == "__main__":
    unittest.main()
