"""
Pruebas unitarias para el descubrimiento de juegos de Epic Games en Linux.
"""

import json
from pathlib import Path
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


if __name__ == "__main__":
    unittest.main()
