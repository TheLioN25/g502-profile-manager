"""
Pruebas unitarias para el descubrimiento de aplicaciones y accesos directos de Steam (shortcuts.vdf).
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
import struct
import sys
import tempfile
import unittest

src_path = Path(__file__).resolve().parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from adapters.steam_discovery import (
    ActiveSteamApplication,
    SteamAppManifest,
    SteamLaunch,
    SteamShortcut,
    discover_active_steam_apps,
    discover_steam_shortcuts,
    parse_binary_vdf,
)
from adapters.process_discovery import ProcessInfo


def _build_synthetic_vdf(shortcuts: list[dict]) -> bytes:
    """Construye un payload binario en formato Valve Binary KeyValues."""
    buf = bytearray()
    buf.append(0x00)
    buf.extend(b"shortcuts\x00")

    for i, s in enumerate(shortcuts):
        buf.append(0x00)
        buf.extend(f"{i}\x00".encode("utf-8"))

        if "appid" in s:
            buf.append(0x02)
            buf.extend(b"appid\x00")
            buf.extend(struct.pack("<I", s["appid"]))

        for str_key in ("AppName", "Exe", "StartDir", "LaunchOptions", "icon", "ShortcutPath"):
            if str_key in s:
                buf.append(0x01)
                buf.extend(f"{str_key}\x00".encode("utf-8"))
                buf.extend(f"{s[str_key]}\x00".encode("utf-8"))

        buf.append(0x08)  # Cierre del shortcut

    buf.append(0x08)  # Cierre de shortcuts
    return bytes(buf)


class TestSteamShortcutsDiscovery(unittest.TestCase):
    """Verifica el decodificador de Valve Binary KeyValues y el descubridor de shortcuts."""

    def test_parse_binary_vdf_empty_or_invalid(self) -> None:
        self.assertEqual(parse_binary_vdf(b""), {})
        self.assertEqual(parse_binary_vdf(b"\x00incomplete"), {})
        self.assertEqual(parse_binary_vdf(b"\xff\xfe\x00"), {})

    def test_parse_binary_vdf_synthetic_success(self) -> None:
        payload = _build_synthetic_vdf([
            {
                "appid": 3519040750,
                "AppName": "Soulframe",
                "Exe": '"/games/Soulframe/Launcher.exe"',
                "StartDir": '"/games/Soulframe/"',
                "LaunchOptions": 'STEAM_COMPAT_MOUNTS="/games" %command%',
                "icon": "launcher.ico",
                "ShortcutPath": "/home/user/.local/share/applications/Soulframe.desktop",
            }
        ])
        result = parse_binary_vdf(payload)
        self.assertIn("shortcuts", result)
        self.assertIn("0", result["shortcuts"])
        entry = result["shortcuts"]["0"]
        self.assertEqual(entry["appid"], 3519040750)
        self.assertEqual(entry["AppName"], "Soulframe")
        self.assertEqual(entry["LaunchOptions"], 'STEAM_COMPAT_MOUNTS="/games" %command%')

    def test_parse_binary_vdf_handles_negative_signed_int32(self) -> None:
        # En C++, -775926546 en int32 con signo equivale a 3519040750 en uint32
        signed_bytes = struct.pack("<i", -775926546)
        buf = bytearray()
        buf.append(0x00)
        buf.extend(b"shortcuts\x00")
        buf.append(0x00)
        buf.extend(b"0\x00")
        buf.append(0x02)
        buf.extend(b"appid\x00")
        buf.extend(signed_bytes)
        buf.append(0x01)
        buf.extend(b"AppName\x00Soulframe\x00")
        buf.append(0x08)
        buf.append(0x08)

        parsed = parse_binary_vdf(bytes(buf))
        self.assertEqual(parsed["shortcuts"]["0"]["appid"], 3519040750)

    def test_discover_steam_shortcuts_mocked_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            user_config = temp_path / "userdata" / "12345678" / "config"
            user_config.mkdir(parents=True, exist_ok=True)
            vdf_file = user_config / "shortcuts.vdf"

            payload = _build_synthetic_vdf([
                {
                    "appid": 3519040750,
                    "AppName": "Soulframe",
                    "Exe": "/path/to/launcher.exe",
                },
                {
                    "appid": 2000000001,
                    "AppName": "Another Non-Steam Game",
                    "Exe": "/path/to/game.exe",
                },
            ])
            vdf_file.write_bytes(payload)

            shortcuts = discover_steam_shortcuts(steam_root=temp_path)
            self.assertEqual(len(shortcuts), 2)
            # Ordenados por nombre: 'Another Non-Steam Game' antes que 'Soulframe'
            self.assertEqual(shortcuts[0].name, "Another Non-Steam Game")
            self.assertEqual(shortcuts[0].app_id, 2000000001)
            self.assertEqual(shortcuts[1].name, "Soulframe")
            self.assertEqual(shortcuts[1].app_id, 3519040750)

    def test_discover_steam_shortcuts_nonexistent_root_returns_empty(self) -> None:
        non_existent = Path("/path/that/does/not/exist_123456789")
        shortcuts = discover_steam_shortcuts(steam_root=non_existent)
        self.assertEqual(shortcuts, [])

    def test_discover_steam_shortcuts_deduplicates_across_users(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            user1_config = temp_path / "userdata" / "1111" / "config"
            user2_config = temp_path / "userdata" / "2222" / "config"
            user1_config.mkdir(parents=True, exist_ok=True)
            user2_config.mkdir(parents=True, exist_ok=True)

            payload = _build_synthetic_vdf([
                {
                    "appid": 3519040750,
                    "AppName": "Soulframe",
                    "Exe": "/path/to/launcher.exe",
                }
            ])
            (user1_config / "shortcuts.vdf").write_bytes(payload)
            (user2_config / "shortcuts.vdf").write_bytes(payload)

            shortcuts = discover_steam_shortcuts(steam_root=temp_path)
            self.assertEqual(len(shortcuts), 1)
            self.assertEqual(shortcuts[0].app_id, 3519040750)

    def test_parse_binary_vdf_truncated_integer_returns_empty(self) -> None:
        # \x02 seguido de clave y solo 2 bytes en lugar de 4 bytes
        truncated_payload = b"\x00shortcuts\x00\x000\x00\x02appid\x00\xee\x4c"
        self.assertEqual(parse_binary_vdf(truncated_payload), {})

    def test_discover_steam_shortcuts_strips_surrounding_quotes_on_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            user_config = temp_path / "userdata" / "437978958" / "config"
            user_config.mkdir(parents=True, exist_ok=True)
            vdf_file = user_config / "shortcuts.vdf"

            payload = _build_synthetic_vdf([
                {
                    "appid": 3519040750,
                    "AppName": "Soulframe",
                    "Exe": '"/games/Soulframe/Downloaded/Public/Tools/Launcher.exe"',
                    "StartDir": '"/games/Soulframe/Downloaded/Public/Tools/"',
                    "ShortcutPath": '"/home/user/.local/share/applications/Soulframe.desktop"',
                }
            ])
            vdf_file.write_bytes(payload)

            shortcuts = discover_steam_shortcuts(steam_root=temp_path)
            self.assertEqual(len(shortcuts), 1)
            s = shortcuts[0]
            self.assertEqual(s.exe, "/games/Soulframe/Downloaded/Public/Tools/Launcher.exe")
            self.assertEqual(s.start_dir, "/games/Soulframe/Downloaded/Public/Tools/")
            self.assertEqual(s.shortcut_path, "/home/user/.local/share/applications/Soulframe.desktop")

    def test_discover_steam_shortcuts_handles_capitalized_shortcuts_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            user_config = temp_path / "userdata" / "9999" / "config"
            user_config.mkdir(parents=True, exist_ok=True)
            vdf_file = user_config / "shortcuts.vdf"

            # Construir payload con 'Shortcuts' con mayúscula
            buf = bytearray()
            buf.append(0x00)
            buf.extend(b"Shortcuts\x00")
            buf.append(0x00)
            buf.extend(b"0\x00")
            buf.append(0x02)
            buf.extend(b"appid\x00")
            buf.extend(struct.pack("<I", 123456))
            buf.append(0x01)
            buf.extend(b"AppName\x00Capitalized Game\x00")
            buf.append(0x08)
            buf.append(0x08)
            vdf_file.write_bytes(bytes(buf))

            shortcuts = discover_steam_shortcuts(steam_root=temp_path)
            self.assertEqual(len(shortcuts), 1)
            self.assertEqual(shortcuts[0].name, "Capitalized Game")
            self.assertEqual(shortcuts[0].app_id, 123456)

    def test_discover_active_steam_apps_resolves_non_steam_shortcut(self) -> None:
        shortcut = SteamShortcut(
            app_id=3519040750,
            name="Soulframe",
            exe="/games/Soulframe/Launcher.exe",
            start_dir="/games/Soulframe/",
        )
        proc = ProcessInfo(
            pid=7777,
            name="reaper",
            executable_path="/usr/bin/pressure-vessel",
            real_executable_path="/usr/bin/pressure-vessel",
            command="pressure-vessel-wrap SteamLaunch AppId=3519040750 -- /games/Soulframe/Launcher.exe",
        )
        dummy_vdf = Path("/tmp/dummy_nonexistent_libraryfolders.vdf")
        active = discover_active_steam_apps([proc], dummy_vdf, shortcuts=[shortcut])
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].manifest.app_id, 3519040750)
        self.assertEqual(active[0].manifest.name, "Soulframe")
        self.assertEqual(active[0].launch.app_id, 3519040750)

    def test_steam_dataclasses_are_immutable(self) -> None:
        """
        [M-01, M-02, M-03, M-04] Verifica que las dataclasses del dominio de Steam
        (SteamLaunch, SteamAppManifest, ActiveSteamApplication y SteamShortcut)
        sean inmutables (frozen=True).
        """
        # [M-01] SteamLaunch
        launch = SteamLaunch(app_id=123, supervisor_pid=456, command="steam -applaunch 123")
        with self.assertRaises(FrozenInstanceError):
            launch.app_id = 999  # type: ignore

        # [M-02] SteamAppManifest
        manifest = SteamAppManifest(
            app_id=123,
            name="Test Game",
            install_dir="/games/test",
            manifest_file="appmanifest_123.acf",
            library_path="/games/steam",
        )
        with self.assertRaises(FrozenInstanceError):
            manifest.name = "Hacked"  # type: ignore

        # [M-03] ActiveSteamApplication
        active = ActiveSteamApplication(launch=launch, manifest=manifest)
        with self.assertRaises(FrozenInstanceError):
            active.launch = launch  # type: ignore

        # [M-04] SteamShortcut
        shortcut = SteamShortcut(
            app_id=3519040750,
            name="Soulframe",
            exe="/games/Soulframe/Launcher.exe",
        )
        with self.assertRaises(FrozenInstanceError):
            shortcut.name = "Hacked"  # type: ignore


if __name__ == "__main__":
    unittest.main()
