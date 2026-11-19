"""
Pruebas unitarias para el adaptador de descubrimiento y filtrado de procesos en Linux (process_discovery).
"""

from dataclasses import FrozenInstanceError
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

src_path = Path(__file__).resolve().parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from adapters.process_discovery import (
    ProcessInfo,
    deduplicate_processes,
    discover_processes,
    extract_executable_name,
    get_effective_executable_path,
    process_name_is_running,
    read_process,
    search_processes,
    should_ignore,
)


class TestProcessDiscoveryAdapter(unittest.TestCase):
    def test_process_info_is_immutable(self) -> None:
        """[M-01] Verifica que ProcessInfo sea una dataclass inmutable (frozen)."""
        proc = ProcessInfo(
            pid=1234,
            name="game.exe",
            executable_path="/games/game.exe",
            real_executable_path="/usr/bin/wine64",
            command="wine game.exe",
        )
        with self.assertRaises(FrozenInstanceError):
            proc.name = "hacked.exe"  # type: ignore

    def test_read_process_single_arg_without_trailing_null(self) -> None:
        """
        [M-02, M-03] Verifica que un comando de un solo argumento sin terminador nulo
        no sufra la eliminación errónea de su único argumento (evitando pop indebido).
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            pid_dir = Path(tmpdir) / "1234"
            pid_dir.mkdir()

            (pid_dir / "comm").write_text("mygame\n", encoding="utf-8")
            (pid_dir / "cmdline").write_bytes(b"/usr/bin/mygame")
            (pid_dir / "exe").symlink_to(Path("/usr/bin/mygame"))

            proc = read_process(pid_dir)
            self.assertIsNotNone(proc)
            assert proc is not None
            self.assertEqual(proc.pid, 1234)
            self.assertEqual(proc.name, "mygame")
            self.assertEqual(proc.executable_path, "/usr/bin/mygame")
            self.assertEqual(proc.command, "/usr/bin/mygame")

    def test_read_process_with_trailing_null(self) -> None:
        """Verifica que argumentos separados por nulo y con terminador nulo se procesen adecuadamente."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pid_dir = Path(tmpdir) / "5678"
            pid_dir.mkdir()

            (pid_dir / "comm").write_text("wine\n", encoding="utf-8")
            (pid_dir / "cmdline").write_bytes(b"wine\x00game.exe\x00--windowed\x00")
            (pid_dir / "exe").symlink_to(Path("/usr/bin/wine"))

            proc = read_process(pid_dir)
            self.assertIsNotNone(proc)
            assert proc is not None
            self.assertEqual(proc.pid, 5678)
            self.assertEqual(proc.name, "wine")
            self.assertEqual(proc.executable_path, "wine")
            self.assertEqual(proc.command, "wine game.exe --windowed")

    def test_read_process_empty_cmdline_returns_none(self) -> None:
        """[M-04] Verifica que si cmdline está vacío se retorne None (no True ni otro valor)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pid_dir = Path(tmpdir) / "9999"
            pid_dir.mkdir()

            (pid_dir / "comm").write_text("kworker\n", encoding="utf-8")
            (pid_dir / "cmdline").write_bytes(b"")
            (pid_dir / "exe").symlink_to(Path("/usr/bin/none"))

            proc = read_process(pid_dir)
            self.assertIsNone(proc)

    def test_read_process_nonexistent_or_unreadable_returns_none(self) -> None:
        """[M-05] Verifica que si el proceso no existe o no es accesible retorne None (no True)."""
        nonexistent_path = Path("/proc/999999999")
        proc = read_process(nonexistent_path)
        self.assertIsNone(proc)

    def test_read_process_empty_name_or_empty_command_returns_none(self) -> None:
        """Verifica que procesos con comm vacío o comando en blanco retornen None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Caso comm vacío
            pid_dir1 = Path(tmpdir) / "101"
            pid_dir1.mkdir()
            (pid_dir1 / "comm").write_text("   \n", encoding="utf-8")
            (pid_dir1 / "cmdline").write_bytes(b"/bin/dummy")
            (pid_dir1 / "exe").symlink_to(Path("/bin/dummy"))
            self.assertIsNone(read_process(pid_dir1))

            # Caso cmdline que se traduce a espacios vacíos
            pid_dir2 = Path(tmpdir) / "102"
            pid_dir2.mkdir()
            (pid_dir2 / "comm").write_text("dummy\n", encoding="utf-8")
            (pid_dir2 / "cmdline").write_bytes(b"  \x00   \x00")
            (pid_dir2 / "exe").symlink_to(Path("/bin/dummy"))
            self.assertIsNone(read_process(pid_dir2))

    def test_should_ignore(self) -> None:
        """Verifica el filtrado de procesos del sistema y auxiliares de Wine/Steam."""
        ignored_system = ProcessInfo(1, "systemd", "/sbin/init", "/sbin/init", "/sbin/init")
        self.assertTrue(should_ignore(ignored_system))

        ignored_aux = ProcessInfo(200, "wineserver", "/usr/bin/wineserver", "/usr/bin/wineserver", "wineserver -p")
        self.assertTrue(should_ignore(ignored_aux))

        ignored_command_part = ProcessInfo(300, "helper", "/usr/bin/steamwebhelper", "/usr/bin/steamwebhelper", "steamwebhelper --type=renderer")
        self.assertTrue(should_ignore(ignored_command_part))

        valid_game = ProcessInfo(400, "Soulframe.x64.exe", "Soulframe.x64.exe", "/games/Soulframe.x64.exe", "wine Soulframe.x64.exe")
        self.assertFalse(should_ignore(valid_game))

    def test_deduplicate_processes(self) -> None:
        """Verifica la deduplicación de procesos con idéntico nombre y comando."""
        proc1 = ProcessInfo(101, "game", "/games/game", "/games/game", "game --opt")
        proc2 = ProcessInfo(102, "game", "/games/game", "/games/game", "game --opt")
        proc3 = ProcessInfo(103, "other", "/games/other", "/games/other", "other")

        deduped = deduplicate_processes([proc1, proc2, proc3])
        self.assertEqual(len(deduped), 2)
        pids = [p.pid for p in deduped]
        self.assertIn(101, pids)
        self.assertNotIn(102, pids)
        self.assertIn(103, pids)

    def test_search_processes(self) -> None:
        """Verifica la búsqueda de procesos por subcadena insensible a mayúsculas."""
        proc1 = ProcessInfo(1, "Warframe.x64.exe", "Warframe.x64.exe", "/games/Warframe.x64.exe", "wine Warframe.x64.exe")
        proc2 = ProcessInfo(2, "discord", "/usr/bin/discord", "/usr/bin/discord", "discord --no-sandbox")
        processes = [proc1, proc2]

        # Búsqueda coincidente en nombre
        results = search_processes("warframe", processes=processes)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Warframe.x64.exe")

        # Búsqueda coincidente en comando
        results2 = search_processes("no-sandbox", processes=processes)
        self.assertEqual(len(results2), 1)
        self.assertEqual(results2[0].name, "discord")

        # Búsqueda vacía devuelve todos
        results3 = search_processes("  ", processes=processes)
        self.assertEqual(len(results3), 2)

    def test_get_effective_executable_path(self) -> None:
        """Verifica que /proc/self/exe resuelva a real_executable_path."""
        proc_self = ProcessInfo(10, "self", "/proc/self/exe", "/usr/bin/real_binary", "/proc/self/exe")
        self.assertEqual(get_effective_executable_path(proc_self), "/usr/bin/real_binary")

        proc_normal = ProcessInfo(20, "game", "/usr/games/bin", "/usr/games/bin", "/usr/games/bin")
        self.assertEqual(get_effective_executable_path(proc_normal), "/usr/games/bin")

    def test_extract_executable_name(self) -> None:
        """Verifica la extracción del ejecutable para rutas Linux y Windows con Wine/Proton."""
        # Ruta Linux
        proc_linux = ProcessInfo(1, "game", "/usr/local/games/cool_game", "/usr/local/games/cool_game", "cool_game")
        self.assertEqual(extract_executable_name(proc_linux), "cool_game")

        # Ruta Windows bajo Wine con backslashes y espacios
        proc_wine = ProcessInfo(2, "game.exe", r"C:\Program Files\My Game\bin64\game_client.exe", "/usr/bin/wine", "wine game")
        self.assertEqual(extract_executable_name(proc_wine), "game_client.exe")

    def test_process_name_is_running(self) -> None:
        """Verifica la detección case-insensitive de procesos en ejecución."""
        proc = ProcessInfo(10, "Warframe.x64.exe", r"Z:\Steam\Warframe.x64.exe", "/usr/bin/wine", "wine Warframe")
        self.assertTrue(process_name_is_running("warframe.x64.exe", processes=[proc]))
        self.assertTrue(process_name_is_running("WARFRAME.X64.EXE", processes=[proc]))
        self.assertFalse(process_name_is_running("other_game.exe", processes=[proc]))

    def test_discover_processes_mocked_proc_dir(self) -> None:
        """Verifica el flujo completo de discover_processes explorando un /proc simulado."""
        with tempfile.TemporaryDirectory() as tmpdir:
            proc_root = Path(tmpdir)
            # Entrada no numérica (debe ser ignorada)
            (proc_root / "cpuinfo").write_text("cpu data\n", encoding="utf-8")

            # Proceso del sistema a descartar
            pid_sys = proc_root / "1"
            pid_sys.mkdir()
            (pid_sys / "comm").write_text("systemd\n", encoding="utf-8")
            (pid_sys / "cmdline").write_bytes(b"/sbin/init\x00")
            (pid_sys / "exe").symlink_to(Path("/sbin/init"))

            # Proceso legítimo
            pid_game = proc_root / "1234"
            pid_game.mkdir()
            (pid_game / "comm").write_text("mygame\n", encoding="utf-8")
            (pid_game / "cmdline").write_bytes(b"/games/mygame\x00--fullscreen\x00")
            (pid_game / "exe").symlink_to(Path("/games/mygame"))

            with patch("adapters.process_discovery.PROC_DIR", proc_root):
                found = discover_processes()
                self.assertEqual(len(found), 1)
                self.assertEqual(found[0].pid, 1234)
                self.assertEqual(found[0].name, "mygame")


if __name__ == "__main__":
    unittest.main()
