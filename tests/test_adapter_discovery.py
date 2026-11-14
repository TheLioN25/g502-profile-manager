"""
Pruebas unitarias para ApplicationDiscoveryAdapter.
"""

from pathlib import Path
import sys
import unittest

src_path = Path(__file__).resolve().parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from adapters import (
    ApplicationDiscoveryAdapter,
    DesktopEntry,
    ProcessInfo,
    SteamAppManifest,
    SteamShortcut,
    extract_steam_app_id,
)
import tempfile


class TestApplicationDiscoveryAdapter(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.dummy_steam_file = Path(self.temp_dir.name) / "libraryfolders.vdf"
        self.dummy_steam_file.write_text('"libraryfolders" {}')
        self.adapter = ApplicationDiscoveryAdapter(steam_libraryfolders_file=self.dummy_steam_file)

    def tearDown(self):
        self.temp_dir.cleanup()

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

    def test_discover_steam_applications_includes_shortcuts(self):
        dummy_manifests = [
            SteamAppManifest(
                app_id=230410,
                name="Warframe",
                install_dir="/games/Warframe",
                manifest_file="appmanifest_230410.acf",
                library_path="/games",
            ),
        ]
        dummy_shortcuts = [
            SteamShortcut(
                app_id=3519040750,
                name="Soulframe",
                exe="/games/Soulframe/Launcher.exe",
            ),
        ]

        apps = self.adapter.discover_steam_applications(
            reader=lambda _: dummy_manifests,
            shortcuts_finder=lambda **_: dummy_shortcuts,
        )

        self.assertEqual(len(apps), 2)
        app_by_id = {a.application_id: a for a in apps}
        self.assertIn("steam:230410", app_by_id)
        self.assertIn("steam:3519040750", app_by_id)
        soulframe = app_by_id["steam:3519040750"]
        self.assertEqual(soulframe.name, "Soulframe")
        self.assertTrue(soulframe.is_game)

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

    def test_extract_steam_app_id_variants(self):
        # 1. Proceso reaper estándar
        proc_reaper = ProcessInfo(
            pid=1001,
            name="reaper",
            executable_path="/usr/bin/reaper",
            real_executable_path="/usr/bin/reaper",
            command="reaper SteamLaunch AppId=230410 -- /games/Warframe.x64",
        )
        self.assertEqual(extract_steam_app_id(proc_reaper), 230410)

        # 2. Proceso srt-bwrap / pressure-vessel sin nombre reaper
        proc_bwrap = ProcessInfo(
            pid=1002,
            name="srt-bwrap",
            executable_path="/usr/bin/srt-bwrap",
            real_executable_path="/usr/bin/srt-bwrap",
            command="/usr/lib/pressure-vessel/bin/srt-bwrap SteamLaunch AppId=1284210 -- /games/GW2.exe",
        )
        self.assertEqual(extract_steam_app_id(proc_bwrap), 1284210)

        # 3. Proceso irrelevante sin SteamLaunch
        proc_other = ProcessInfo(
            pid=1003,
            name="bash",
            executable_path="/usr/bin/bash",
            real_executable_path="/usr/bin/bash",
            command="/bin/bash -i",
        )
        self.assertIsNone(extract_steam_app_id(proc_other))


    def test_parse_desktop_entry_localization(self):
        from adapters import parse_desktop_entry

        desktop_file = Path(self.temp_dir.name) / "test_app.desktop"
        desktop_file.write_text(
            "[Desktop Entry]\n"
            "Type=Application\n"
            "Name=System Settings\n"
            "Name[es]=Preferencias del sistema\n"
            "Exec=systemsettings\n"
        )

        # En español
        entry_es = parse_desktop_entry(desktop_file, lang="es")
        self.assertIsNotNone(entry_es)
        self.assertEqual(entry_es.name, "Preferencias del sistema")

        # En inglés
        entry_en = parse_desktop_entry(desktop_file, lang="en")
        self.assertIsNotNone(entry_en)
        self.assertEqual(entry_en.name, "System Settings")

    def test_discover_desktop_entries_recursive(self):
        from adapters.desktop_entries import discover_desktop_entries

        sub_dir = Path(self.temp_dir.name) / "wine" / "Programs" / "Game"
        sub_dir.mkdir(parents=True, exist_ok=True)
        root_desktop = Path(self.temp_dir.name) / "root_app.desktop"
        nested_desktop = sub_dir / "nested_game.desktop"

        root_desktop.write_text("[Desktop Entry]\nType=Application\nName=Root\nExec=root\n")
        nested_desktop.write_text("[Desktop Entry]\nType=Application\nName=Nested\nExec=nested\n")

        found = discover_desktop_entries(directories=[self.temp_dir.name])
        found_names = {p.name for p in found}

        self.assertIn("root_app.desktop", found_names)
        self.assertIn("nested_game.desktop", found_names)

    def test_parse_desktop_entry_wine_with_wmclass(self):
        from adapters import parse_desktop_entry

        desktop_file = Path(self.temp_dir.name) / "soulframe.desktop"
        desktop_file.write_text(
            "[Desktop Entry]\n"
            "Name=Soulframe\n"
            'Exec=env "WINEPREFIX=/home/user/.wine" wine "C:\\\\users\\\\user\\\\Soulframe.lnk"\n'
            "Type=Application\n"
            "StartupWMClass=launcher.exe\n"
        )

        entry = parse_desktop_entry(desktop_file)
        self.assertIsNotNone(entry)
        self.assertEqual(entry.name, "Soulframe")
        self.assertEqual(entry.executable, "launcher.exe")
        self.assertEqual(entry.startup_wm_class, "launcher.exe")
        self.assertTrue(entry.is_game)

    def test_parse_desktop_entry_wine_without_wmclass_extracts_target(self):
        from adapters import parse_desktop_entry

        desktop_file = Path(self.temp_dir.name) / "game_exe.desktop"
        desktop_file.write_text(
            "[Desktop Entry]\n"
            "Name=My Game\n"
            'Exec=wine "C:\\\\Games\\\\MyGame\\\\Game.exe"\n'
            "Type=Application\n"
        )

        entry = parse_desktop_entry(desktop_file)
        self.assertIsNotNone(entry)
        self.assertEqual(entry.name, "My Game")
        self.assertEqual(entry.executable, "Game.exe")
        self.assertIsNone(entry.startup_wm_class)
        self.assertTrue(entry.is_game)

    def test_build_desktop_entry_index_includes_startup_wm_class(self):
        from adapters.application_resolver import build_desktop_entry_index

        entry = DesktopEntry(
            name="Soulframe",
            executable="soulframe",
            exec_value="wine Soulframe.lnk",
            desktop_file="/path/to/soulframe.desktop",
            startup_wm_class="launcher.exe",
        )

        index = build_desktop_entry_index([entry])
        self.assertIn("soulframe", index)
        self.assertIn("launcher.exe", index)
        self.assertEqual(index["soulframe"][0].name, "Soulframe")
        self.assertEqual(index["launcher.exe"][0].name, "Soulframe")


if __name__ == "__main__":
    unittest.main()
