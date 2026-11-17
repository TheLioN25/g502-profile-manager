"""
Pruebas unitarias para ApplicationResolver (resolución dinámica de procesos y binarios secundarios).
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
import sys
import unittest

src_path = Path(__file__).resolve().parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from adapters.application_resolver import (
    ActiveApplication,
    build_desktop_entry_index,
    combine_active_applications,
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
        self.assertEqual(app.application_id, "desktop:soulframe")
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
        self.assertEqual(app.application_id, "desktop:soulframe")
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
        self.assertEqual(app.application_id, "desktop:soulframe")
        self.assertEqual(app.executable, "UnlistedHelper.exe")

    def test_tree_heuristic_does_not_cross_attribute_games_under_program_files(self) -> None:
        # Dos juegos distintos bajo Program Files
        entry_game_a = DesktopEntry(
            name="Game A",
            executable="gamea.exe",
            exec_value='wine "C:\\Program Files\\GameA\\GameA.exe"',
            desktop_file="/path/to/gamea.desktop",
            is_game=True,
        )
        proc_game_b = ProcessInfo(
            pid=8888,
            name="GameB.exe",
            executable_path="C:\\Program Files\\GameB\\GameB.exe",
            real_executable_path="/usr/bin/wine64-preloader",
            command='"C:\\Program Files\\GameB\\GameB.exe"',
        )
        # GameB no debe asociarse a GameA por el directorio padre Program Files
        resolved = resolve_active_applications([proc_game_b], [entry_game_a], alias_map=None)
        self.assertEqual(len(resolved), 0)

    def test_unrelated_game_with_generic_launcher_does_not_hijack_soulframe_alias(self) -> None:
        # Entrada de otro juego que casualmente usa Launcher.exe
        unrelated_entry = DesktopEntry(
            name="Other RPG",
            executable="launcher.exe",
            exec_value='wine "C:\\Games\\OtherRPG\\Launcher.exe"',
            desktop_file="/path/to/other_rpg.desktop",
            is_game=True,
        )
        index = build_desktop_entry_index([unrelated_entry], alias_map=self.alias_map)
        # No debe asociar soulframe.x64.exe a Other RPG
        self.assertNotIn("soulframe.x64.exe", index)

        proc_unrelated = ProcessInfo(
            pid=4321,
            name="Launcher.exe",
            executable_path="C:\\Games\\OtherRPG\\Launcher.exe",
            real_executable_path="/usr/bin/wine64-preloader",
            command="wine Launcher.exe",
        )
        resolved = resolve_active_applications([proc_unrelated], [unrelated_entry], alias_map=self.alias_map)
        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0].name, "Other RPG")
        self.assertEqual(resolved[0].application_id, "desktop:other_rpg")
        self.assertNotEqual(resolved[0].application_id, "desktop:soulframe")

    def test_active_application_is_immutable(self) -> None:
        """Verifica que ActiveApplication sea una dataclass inmutable (frozen)."""
        app = ActiveApplication(
            name="Test",
            application_id="desktop:test",
            source="desktop",
            executable="test",
            desktop_files=(),
            process_ids=(),
            ambiguous=False,
            is_game=False,
        )
        with self.assertRaises(FrozenInstanceError):
            app.name = "Modified"  # type: ignore

    def test_active_application_default_is_game_is_false(self) -> None:
        """Verifica que el campo is_game sea False por defecto en ActiveApplication."""
        app = ActiveApplication(
            name="Test",
            application_id="desktop:test",
            source="desktop",
            executable="test",
            desktop_files=(),
            process_ids=(),
            ambiguous=False,
        )
        self.assertFalse(app.is_game)

    def test_build_desktop_entry_index_handles_non_dict_alias_map(self) -> None:
        """Verifica que valores no-diccionario en alias_map no provoquen errores."""
        index = build_desktop_entry_index([self.soulframe_entry], alias_map="invalid_string")  # type: ignore
        self.assertIn("launcher.exe", index)
        index2 = build_desktop_entry_index([self.soulframe_entry], alias_map=123)  # type: ignore
        self.assertIn("launcher.exe", index2)

    def test_combine_active_applications_prioritizes_games(self) -> None:
        """Verifica que combine_active_applications ordene juegos antes que utilidades de escritorio."""
        desktop_util = ActiveApplication(
            name="Brave Browser",
            application_id="desktop:brave",
            source="desktop",
            executable="brave",
            desktop_files=(),
            process_ids=(1,),
            ambiguous=False,
            is_game=False,
        )
        steam_game = ActiveApplication(
            name="Soulframe",
            application_id="steam:3519040750",
            source="steam",
            executable="Soulframe.x64.exe",
            desktop_files=(),
            process_ids=(2,),
            ambiguous=False,
            is_game=True,
        )
        combined = combine_active_applications([[desktop_util], [steam_game]])
        self.assertEqual(len(combined), 2)
        # El juego debe quedar en primera posición aunque alfabéticamente "Brave" < "Soulframe"
        self.assertEqual(combined[0].application_id, "steam:3519040750")
        self.assertEqual(combined[1].application_id, "desktop:brave")


if __name__ == "__main__":
    unittest.main()
