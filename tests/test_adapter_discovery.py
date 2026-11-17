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
    EpicAppManifest,
    ProcessInfo,
    SteamAppManifest,
    SteamShortcut,
    extract_steam_app_id,
)
from adapters.desktop_entries import extract_exec_name
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
        # M-02: Verificar que todos los juegos de Steam se marquen como is_game=True
        self.assertTrue(all(a.is_game for a in apps), "Todos los juegos de Steam deben tener is_game=True")

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

    def test_discover_steam_guard_skips_default_reader_when_file_missing(self):
        """
        M-01: Verifica la guarda lógica de la línea 63.
        Con el lector por defecto y sin archivo en disco, debe devolver [].
        Con un lector inyectado y sin archivo en disco, SÍ debe ejecutarse.
        """
        from adapters.steam_discovery import discover_installed_steam_apps

        # Adaptador apuntando a un archivo que NO existe
        missing_file = Path(self.temp_dir.name) / "no_existe.vdf"
        adapter_no_file = ApplicationDiscoveryAdapter(steam_libraryfolders_file=missing_file)

        # Con lector por defecto y archivo inexistente: la guarda impide la lectura → []
        apps_default = adapter_no_file.discover_steam_applications(
            reader=discover_installed_steam_apps,
            shortcuts_finder=lambda **_: [],
        )
        self.assertEqual(apps_default, [])

        # Con lector inyectado personalizado y archivo inexistente: la guarda NO impide → se ejecuta
        dummy = [SteamAppManifest(app_id=999, name="TestGame", install_dir="/g", manifest_file="m.acf", library_path="/g")]
        apps_custom = adapter_no_file.discover_steam_applications(
            reader=lambda _: dummy,
            shortcuts_finder=lambda **_: [],
        )
        self.assertEqual(len(apps_custom), 1)
        self.assertEqual(apps_custom[0].application_id, "steam:999")
        self.assertTrue(apps_custom[0].is_game)

    def test_discover_epic_applications_mocked(self):
        """
        M-03: Verifica que discover_epic_applications marque is_game=True
        y retorne aplicaciones ordenadas alfabéticamente.
        """
        dummy_epic = [
            EpicAppManifest(app_name="zephyr-123", title="Zephyr Online", install_path="/games/Zephyr"),
            EpicAppManifest(app_name="aion-456", title="AION 2", install_path="/games/AION2"),
        ]

        apps = self.adapter.discover_epic_applications(finder=lambda: dummy_epic)

        self.assertEqual(len(apps), 2)
        # Verificar orden alfabético (AION 2 antes de Zephyr Online)
        self.assertEqual(apps[0].name, "AION 2")
        self.assertEqual(apps[1].name, "Zephyr Online")
        # Verificar IDs (app_id es propiedad derivada: "epic:" + app_name)
        self.assertEqual(apps[0].application_id, "epic:aion-456")
        self.assertEqual(apps[1].application_id, "epic:zephyr-123")
        # M-03: Verificar que TODOS sean is_game=True
        self.assertTrue(all(a.is_game for a in apps), "Todos los juegos de Epic deben tener is_game=True")

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

    def test_parse_desktop_entry_wine_utilities_not_classified_as_game(self):
        from adapters import parse_desktop_entry

        for util_cmd in ["winecfg", "winetricks", "wine wineboot.exe", "wine uninstaller.exe"]:
            desktop_file = Path(self.temp_dir.name) / f"util_{util_cmd.split()[-1]}.desktop"
            desktop_file.write_text(
                "[Desktop Entry]\n"
                f"Name=Wine Util {util_cmd}\n"
                f"Exec={util_cmd}\n"
                "Type=Application\n"
            )
            entry = parse_desktop_entry(desktop_file)
            self.assertIsNotNone(entry)
            self.assertFalse(entry.is_game, f"{util_cmd} should not be classified as a game")

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

    # --- Tests de blindaje para desktop_entries.py (Módulo 2 del Diario) ---

    def test_desktop_entry_is_immutable(self):
        """M-01: DesktopEntry debe ser frozen (inmutable)."""
        entry = DesktopEntry(
            name="Test", executable="test", exec_value="test", desktop_file="/tmp/t.desktop"
        )
        with self.assertRaises(AttributeError):
            entry.name = "Modified"

    def test_desktop_entry_default_is_game_is_false(self):
        """M-02: El default de is_game debe ser False cuando no se pasa explícitamente."""
        entry = DesktopEntry(
            name="Blender", executable="blender", exec_value="blender %f", desktop_file="/tmp/b.desktop"
        )
        self.assertFalse(entry.is_game, "is_game debe ser False por defecto")

    def test_extract_exec_name_returns_none_for_empty_input(self):
        """M-03: extract_exec_name con input vacío debe retornar None."""
        self.assertIsNone(extract_exec_name(""))
        self.assertIsNone(extract_exec_name(None))

    def test_extract_exec_name_returns_none_for_malformed_quotes(self):
        """M-04: extract_exec_name con comillas desbalanceadas (ValueError en shlex) debe retornar None."""
        self.assertIsNone(extract_exec_name('wine "broken'))

    def test_extract_exec_name_returns_none_when_only_env_variables(self):
        """M-05: extract_exec_name con solo env y variables sin binario debe retornar None."""
        self.assertIsNone(extract_exec_name("env FOO=bar BAZ=qux"))


if __name__ == "__main__":
    unittest.main()
