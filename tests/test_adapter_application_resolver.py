"""
Pruebas unitarias para ApplicationResolver (resolución dinámica de procesos y binarios secundarios).
"""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

src_path = Path(__file__).resolve().parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from adapters.application_resolver import (
    ActiveApplication,
    build_desktop_entry_index,
    resolve_active_applications,
)
from adapters.desktop_entries import DesktopEntry
from adapters.process_discovery import ProcessInfo


class TestApplicationResolver(unittest.TestCase):
    """Verifica la resolución dinámica de procesos hacia aplicaciones y perfiles."""

    def setUp(self) -> None:
        self.soulframe_entry = DesktopEntry(
            name="Soulframe",
            executable="Launcher.exe",
            exec_value='env WINEPREFIX="/home/user/.wine" wine "/home/user/.wine/drive_c/users/user/AppData/Local/Soulframe/Downloaded/Public/Tools/Launcher.exe"',
            desktop_file="/home/user/.local/share/applications/Soulframe.desktop",
            startup_wm_class="launcher.exe",
            is_game=True,
        )

        self.alias_map = {
            "desktop:launcher.exe": "soulframe",
            "launcher.exe": "soulframe",
            "soulframe": "soulframe",
            "soulframe.x64.exe": "soulframe",
            "steam:3519040750": "soulframe",
        }

    def test_build_desktop_entry_index_includes_secondary_aliases(self) -> None:
        index = build_desktop_entry_index([self.soulframe_entry], alias_map=self.alias_map)
        self.assertIn("launcher.exe", index)
        self.assertIn("soulframe.x64.exe", index)
        self.assertIn(self.soulframe_entry, index["launcher.exe"])
        self.assertIn(self.soulframe_entry, index["soulframe.x64.exe"])

    def test_resolve_active_applications_primary_launcher(self) -> None:
        proc = ProcessInfo(
            pid=1234,
            name="Launcher.exe",
            executable_path="C:\\Tools\\Launcher.exe",
            real_executable_path="/usr/bin/wine64-preloader",
            command="wine Launcher.exe",
        )
        resolved = resolve_active_applications([proc], [self.soulframe_entry], alias_map=self.alias_map)
        self.assertEqual(len(resolved), 1)
        app = resolved[0]
        self.assertEqual(app.name, "Soulframe")
        self.assertEqual(app.application_id, "desktop:launcher.exe")
        self.assertEqual(app.executable, "Launcher.exe")

    def test_resolve_active_applications_secondary_binary_soulframe_x64(self) -> None:
        proc = ProcessInfo(
            pid=5678,
            name="Soulframe.x64.exe",
            executable_path="Z:\\games\\Soulframe\\Downloaded\\Public\\Soulframe.x64.exe",
            real_executable_path="/usr/bin/wine64-preloader",
            command='"Z:\\games\\Soulframe\\Downloaded\\Public\\Soulframe.x64.exe" -silent',
        )
        resolved = resolve_active_applications([proc], [self.soulframe_entry], alias_map=self.alias_map)
        self.assertEqual(len(resolved), 1)
        app = resolved[0]
        self.assertEqual(app.name, "Soulframe")
        self.assertEqual(app.application_id, "desktop:launcher.exe")
        self.assertEqual(app.executable, "Soulframe.x64.exe")

    def test_resolve_active_applications_tree_heuristic_fallback(self) -> None:
        # Proceso auxiliar sin alias explícito, pero que corre bajo el árbol del juego
        proc = ProcessInfo(
            pid=9999,
            name="UnlistedHelper.exe",
            executable_path="/home/user/.wine/drive_c/users/user/AppData/Local/Soulframe/Downloaded/Public/Tools/UnlistedHelper.exe",
            real_executable_path="/usr/bin/wine64-preloader",
            command="/home/user/.wine/drive_c/users/user/AppData/Local/Soulframe/Downloaded/Public/Tools/UnlistedHelper.exe",
        )
        # Sin pasar alias_map, para forzar el uso de la heurística de subárbol
        resolved = resolve_active_applications([proc], [self.soulframe_entry], alias_map=None)
        self.assertEqual(len(resolved), 1)
        app = resolved[0]
        self.assertEqual(app.name, "Soulframe")
        self.assertEqual(app.application_id, "desktop:launcher.exe")
        self.assertEqual(app.executable, "UnlistedHelper.exe")


if __name__ == "__main__":
    unittest.main()
