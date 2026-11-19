"""
Pruebas unitarias para el descubrimiento de juegos de Epic Games en Linux.
"""

from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

src_path = Path(__file__).resolve().parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from adapters import (
    EpicAppManifest,
    ProcessInfo,
    discover_active_epic_apps,
    discover_heroic_installed_apps,
    resolve_epic_applications,
)
from adapters.epic_discovery import discover_lutris_epic_apps


class TestEpicDiscovery(unittest.TestCase):
    def test_epic_app_manifest(self):
        manifest = EpicAppManifest(
            app_name="Sugar",
            title="Fall Guys",
            install_path="/games/FallGuys",
            executable="FallGuys_client.exe",
        )
        self.assertEqual(manifest.app_id, "epic:Sugar")
        self.assertEqual(manifest.title, "Fall Guys")

    def test_discover_heroic_installed_apps_mocked(self):
        dummy_data = {
            "Fortnite": {
                "app_name": "Fortnite",
                "title": "Fortnite",
                "install_path": "/games/Fortnite",
                "executable": "FortniteClient-Win64-Shipping.exe",
            },
            "RocketLeague": {
                "app_name": "RocketLeague",
                "title": "Rocket League",
                "install_path": "/games/RocketLeague",
                "executable": "Binaries/Win64/RocketLeague.exe",
            },
        }

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(dummy_data, f)
            temp_path = Path(f.name)

        try:
            apps = discover_heroic_installed_apps([temp_path])
            self.assertEqual(len(apps), 2)
            titles = {a.title for a in apps}
            self.assertIn("Fortnite", titles)
            self.assertIn("Rocket League", titles)
        finally:
            temp_path.unlink(missing_ok=True)

    def test_discover_active_epic_apps_by_cmdline(self):
        installed = [
            EpicAppManifest(
                app_name="Fortnite",
                title="Fortnite",
                install_path="/games/Fortnite",
                executable="FortniteClient.exe",
            )
        ]

        dummy_processes = [
            ProcessInfo(
                pid=1001,
                name="legendary",
                command="legendary launch Fortnite --no-wine",
                executable_path="/usr/bin/legendary",
                real_executable_path="/usr/bin/legendary",
            ),
            ProcessInfo(
                pid=1002,
                name="bash",
                command="bash",
                executable_path="/bin/bash",
                real_executable_path="/bin/bash",
            ),
        ]

        active = discover_active_epic_apps(dummy_processes, installed_apps=installed)
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].app_id, "epic:Fortnite")

    def test_resolve_epic_applications(self):
        manifests = [
            EpicAppManifest(
                app_name="Cyberpunk",
                title="Cyberpunk 2077",
                install_path="/games/CP2077",
                executable="bin/x64/Cyberpunk2077.exe",
            )
        ]

        resolved = resolve_epic_applications(manifests)
        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0].application_id, "epic:Cyberpunk")
        self.assertEqual(resolved[0].name, "Cyberpunk 2077")
        self.assertEqual(resolved[0].source, "epic")
        self.assertTrue(resolved[0].is_game)

    def test_epic_app_manifest_is_immutable(self) -> None:
        """Verifica que EpicAppManifest sea una dataclass inmutable (frozen)."""
        manifest = EpicAppManifest(
            app_name="Sugar",
            title="Fall Guys",
            install_path="/games/FallGuys",
            executable="FallGuys_client.exe",
        )
        with self.assertRaises(FrozenInstanceError):
            manifest.title = "Changed"  # type: ignore

    def test_discover_heroic_installed_apps_fallback_when_app_name_missing(self) -> None:
        """Verifica que si app_name falta en el JSON, se use app_key como fallback."""
        dummy_data = {
            "GameWithoutAppName": {
                "title": "Some Game",
                "install_path": "/games/SomeGame",
                "executable": "game.exe",
            }
        }
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(dummy_data, f)
            temp_path = Path(f.name)

        try:
            apps = discover_heroic_installed_apps([temp_path])
            self.assertEqual(len(apps), 1)
            self.assertEqual(apps[0].app_name, "GameWithoutAppName")
        finally:
            temp_path.unlink(missing_ok=True)

    def test_discover_lutris_epic_apps_mocked(self) -> None:
        """Verifica el descubrimiento de juegos de Epic en la base de datos de Lutris."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            temp_db_path = Path(f.name)

        try:
            conn = sqlite3.connect(temp_db_path)
            cursor = conn.cursor()
            cursor.execute(
                "CREATE TABLE games (slug TEXT, name TEXT, directory TEXT, service TEXT, installer_slug TEXT)"
            )
            cursor.executemany(
                "INSERT INTO games VALUES (?, ?, ?, ?, ?)",
                [
                    ("fall-guys", "Fall Guys", "/games/fallguys", "epic", None),
                    ("fortnite", "Fortnite", "/games/fortnite", "wine", "epic-games-store"),
                    ("portal", "Portal", "/games/portal", "steam", None),
                    ("", "Empty Slug", "/games/empty", "epic", None),
                ],
            )
            conn.commit()
            conn.close()

            apps = discover_lutris_epic_apps(db_path=temp_db_path)
            self.assertEqual(len(apps), 2)
            by_name = {app.app_name: app for app in apps}
            self.assertIn("fall-guys", by_name)
            self.assertIn("fortnite", by_name)
            self.assertEqual(by_name["fall-guys"].app_id, "epic:fall-guys")
            self.assertEqual(by_name["fall-guys"].title, "Fall Guys")
            self.assertEqual(by_name["fall-guys"].install_path, "/games/fallguys")
            self.assertEqual(by_name["fortnite"].app_id, "epic:fortnite")
            self.assertEqual(by_name["fortnite"].title, "Fortnite")
        finally:
            temp_db_path.unlink(missing_ok=True)

    def test_discover_lutris_epic_apps_missing_db(self) -> None:
        """Verifica que si la base de datos no existe retorne una lista vacía de forma segura."""
        nonexistent = Path(tempfile.gettempdir()) / "nonexistent_lutris_test.db"
        apps = discover_lutris_epic_apps(db_path=nonexistent)
        self.assertEqual(apps, [])


if __name__ == "__main__":
    unittest.main()
