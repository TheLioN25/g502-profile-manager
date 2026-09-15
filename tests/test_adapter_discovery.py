"""
Pruebas unitarias para ApplicationDiscoveryAdapter.
"""

from pathlib import Path
import sys
import unittest

src_path = Path(__file__).resolve().parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from adapters import ApplicationDiscoveryAdapter
from desktop_entries import DesktopEntry
from steam_discovery import SteamAppManifest


class TestApplicationDiscoveryAdapter(unittest.TestCase):
    def setUp(self):
        self.adapter = ApplicationDiscoveryAdapter()

    def test_discover_steam_applications_mocked(self):
        dummy_manifests = [
            SteamAppManifest(
                app_id=230410,
                name="Warframe",
                install_dir="/games/Warframe",
                manifest_file="appmanifest_230410.acf",
                library_path="/games",
            ),
            SteamAppManifest(
                app_id=1284210,
                name="Guild Wars 2",
                install_dir="/games/GW2",
                manifest_file="appmanifest_1284210.acf",
                library_path="/games",
            ),
        ]

        # Inyectamos lector simulado
        apps = self.adapter.discover_steam_applications(
            reader=lambda _: dummy_manifests
        )

        self.assertEqual(len(apps), 2)
        app_ids = {a.application_id for a in apps}
        self.assertIn("steam:230410", app_ids)
        self.assertIn("steam:1284210", app_ids)

    def test_discover_desktop_applications_mocked(self):
        dummy_files = [Path("/dummy/blender.desktop"), Path("/dummy/gimp.desktop")]

        def dummy_parser(path: Path):
            if "blender" in path.name:
                return DesktopEntry(
                    name="Blender",
                    executable="blender",
                    exec_value="blender %f",
                    desktop_file=str(path),
                )
            return DesktopEntry(
                name="GIMP",
                executable="gimp-2.10",
                exec_value="gimp-2.10",
                desktop_file=str(path),
            )

        apps = self.adapter.discover_desktop_applications(
            finder=lambda _: dummy_files,
            parser=dummy_parser,
        )

        self.assertEqual(len(apps), 2)
        app_ids = {a.application_id for a in apps}
        self.assertIn("desktop:blender", app_ids)
        self.assertIn("desktop:gimp-2.10", app_ids)

    def test_discover_all_applications_includes_desktop_general_first(self):
        apps = self.adapter.discover_all_applications()
        self.assertGreaterEqual(len(apps), 1)
        self.assertEqual(apps[0].application_id, "desktop:general")
        self.assertEqual(apps[0].name, "Escritorio / Sistema")

    def test_get_application_by_id_desktop_general(self):
        app = self.adapter.get_application_by_id("desktop:general")
        self.assertIsNotNone(app)
        self.assertEqual(app.application_id, "desktop:general")
        self.assertEqual(app.name, "Escritorio / Sistema")


if __name__ == "__main__":
    unittest.main()
