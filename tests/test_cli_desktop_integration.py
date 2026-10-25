"""
Pruebas unitarias para la integración con el entorno de escritorio (CLI install/uninstall desktop).
"""

import configparser
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

src_path = Path(__file__).resolve().parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from cli import (
    cmd_install_bin,
    cmd_install_desktop,
    cmd_install_service,
    cmd_uninstall_bin,
    cmd_uninstall_desktop,
    cmd_uninstall_service,
    create_parser,
)


class TestCliDesktopIntegration(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.fake_home = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_cli_parser_has_desktop_commands(self):
        parser = create_parser()
        args_install = parser.parse_args(["install-desktop"])
        self.assertEqual(args_install.command, "install-desktop")

        args_uninstall = parser.parse_args(["uninstall-desktop"])
        self.assertEqual(args_uninstall.command, "uninstall-desktop")

        args_svc_in = parser.parse_args(["install-service"])
        self.assertEqual(args_svc_in.command, "install-service")

        args_svc_un = parser.parse_args(["uninstall-service"])
        self.assertEqual(args_svc_un.command, "uninstall-service")

    @patch("subprocess.run")
    def test_cmd_install_and_uninstall_desktop(self, mock_subprocess):
        with patch("pathlib.Path.home", return_value=self.fake_home):
            # 1. Ejecutar instalación
            cmd_install_desktop(None)

            dest_desktop = self.fake_home / ".local/share/applications/io.github.thelion.G502ProfileManager.desktop"
            dest_icon = self.fake_home / ".local/share/icons/hicolor/scalable/apps/io.github.thelion.G502ProfileManager.svg"

            self.assertTrue(dest_desktop.exists(), "El archivo .desktop debe existir tras la instalación.")
            self.assertTrue(dest_icon.exists(), "El icono SVG debe existir tras la instalación.")

            # Validar formato del archivo .desktop
            config = configparser.ConfigParser(interpolation=None)
            config.read(dest_desktop, encoding="utf-8")
            self.assertIn("Desktop Entry", config.sections())
            entry = config["Desktop Entry"]
            self.assertEqual(entry["Name"], "G502 Profile Manager")
            self.assertEqual(entry["Icon"], "io.github.thelion.G502ProfileManager")
            self.assertEqual(entry["StartupWMClass"], "io.github.thelion.G502ProfileManager")
            self.assertIn("gui", entry["Exec"])

            # 2. Ejecutar desinstalación
            cmd_uninstall_desktop(None)
            self.assertFalse(dest_desktop.exists(), "El archivo .desktop debe haberse eliminado.")
            self.assertFalse(dest_icon.exists(), "El icono SVG debe haberse eliminado.")

    @patch("subprocess.run")
    def test_cmd_install_and_uninstall_service(self, mock_subprocess):
        mock_proc = unittest.mock.MagicMock()
        mock_proc.stdout = "active"
        mock_subprocess.return_value = mock_proc

        with patch("pathlib.Path.home", return_value=self.fake_home):
            # Preparar launcher simulado en ~/.local/bin/g502
            fake_bin = self.fake_home / ".local/bin"
            fake_bin.mkdir(parents=True, exist_ok=True)
            fake_launcher = fake_bin / "g502"
            fake_launcher.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            fake_launcher.chmod(0o755)

            with patch("shutil.which", return_value=str(fake_launcher)):
                # 1. Instalar servicio systemd
                cmd_install_service(None)

                service_file = self.fake_home / ".config/systemd/user/g502-profile-manager.service"
                self.assertTrue(service_file.exists(), "El archivo .service debe existir tras la instalación.")

                # Validar estructura INI del servicio systemd
                config = configparser.ConfigParser(interpolation=None)
                config.read(service_file, encoding="utf-8")
                self.assertIn("Unit", config.sections())
                self.assertIn("Service", config.sections())
                self.assertIn("Install", config.sections())
                self.assertIn("run", config["Service"]["ExecStart"])
                self.assertNotIn("src/cli.py", config["Service"]["ExecStart"])
                self.assertEqual(config["Install"]["WantedBy"], "default.target")

            # Si el launcher no existe en PATH ni en ~/.local/bin, debe advertir y retornar 1
            fake_launcher.unlink()
            with patch("shutil.which", return_value=None):
                res = cmd_install_service(None)
                self.assertEqual(res, 1)

            # 2. Desinstalar servicio systemd
            cmd_uninstall_service(None)
            self.assertFalse(service_file.exists(), "El archivo .service debe haberse eliminado.")

    def test_cmd_install_and_uninstall_bin(self):
        with patch("pathlib.Path.home", return_value=self.fake_home):
            with patch("subprocess.run") as mock_run:
                cmd_install_bin(None)
                mock_run.assert_called_once()
                self.assertIn("install-bin.sh", mock_run.call_args[0][0][0])

            with patch("subprocess.run") as mock_run:
                cmd_uninstall_bin(None)
                mock_run.assert_called_once()
                self.assertIn("uninstall-bin.sh", mock_run.call_args[0][0][0])

    @patch("cli.AutomationEngine")
    def test_cmd_run_instantiates_engine_correctly(self, mock_engine_cls):
        mock_instance = unittest.mock.MagicMock()
        mock_engine_cls.return_value = mock_instance

        from cli import cmd_run
        args = unittest.mock.MagicMock()
        args.interval = 3.5

        cmd_run(args)
        mock_engine_cls.assert_called_once()
        self.assertEqual(mock_engine_cls.call_args.kwargs["check_interval"], 3.5)
        mock_instance.run.assert_called_once()

    def test_cli_add_action_invalid_key_returns_code_1(self):
        import sys
        from cli import main
        test_argv = ["g502", "add-action", "test:app", "test_act", "Test Action", "INVALID_UNRECOGNIZED_KEY_12345"]
        with patch.object(sys, "argv", test_argv):
            exit_code = main()
            self.assertEqual(exit_code, 1)

    def test_cli_create_corrupted_repo_returns_code_1(self):
        import os
        import sys
        import tempfile
        from cli import main

        with tempfile.TemporaryDirectory() as tmp_home:
            cfg_dir = Path(tmp_home) / ".config"
            cfg_dir.mkdir(parents=True, exist_ok=True)
            prof_file = cfg_dir / "g502-profiles.json"
            prof_file.write_text("CORRUPTED JSON {", encoding="utf-8")

            test_argv = ["g502", "create", "test:app", "Corrupt Test"]
            with patch.dict(os.environ, {"HOME": tmp_home}):
                with patch.object(sys, "argv", test_argv):
                    exit_code = main()
                    self.assertEqual(exit_code, 1)

    def test_cli_assign_invalid_profile_returns_code_1(self):
        import sys
        from cli import main
        test_argv = ["g502", "assign", "nonexistent-profile-id-9999", "G5", "some_action"]
        with patch.object(sys, "argv", test_argv):
            exit_code = main()
            self.assertEqual(exit_code, 1)
    def test_cli_import_non_existent_file_returns_code_1(self):
        import sys
        from cli import main
        test_argv = ["g502", "import", "/tmp/non_existent_file_123456789.json"]
        with patch.object(sys, "argv", test_argv):
            exit_code = main()
            self.assertEqual(exit_code, 1)

    def test_cli_import_invalid_json_returns_code_1(self):
        import sys
        import tempfile
        from cli import main
        with tempfile.NamedTemporaryFile(suffix=".json") as f:
            f.write(b"NOT A VALID JSON {")
            f.flush()
            test_argv = ["g502", "import", f.name]
            with patch.object(sys, "argv", test_argv):
                exit_code = main()
                self.assertEqual(exit_code, 1)

    def test_cli_export_invalid_destination_returns_code_1(self):
        import sys
        from cli import main
        test_argv = ["g502", "export", "/proc/invalid_backup_destination.json"]
        with patch.object(sys, "argv", test_argv):
            exit_code = main()
            self.assertEqual(exit_code, 1)

    def test_cli_subprocess_returns_proper_exit_codes(self):
        import subprocess
        import sys
        cli_script = Path(__file__).resolve().parent.parent / "src/cli.py"

        # Import inexistente en proceso real
        res = subprocess.run([sys.executable, str(cli_script), "import", "/tmp/non_existent_g502.json"], capture_output=True)
        self.assertEqual(res.returncode, 1)

        # Export a destino inválido en proceso real
        res = subprocess.run([sys.executable, str(cli_script), "export", "/proc/unwritable.json"], capture_output=True)
        self.assertEqual(res.returncode, 1)
    def test_cli_export_and_import_success_returns_code_0(self):
        import os
        import sys
        import tempfile
        from cli import main
        from services import ProfileManager
        from storage import JsonProfileRepository

        with tempfile.TemporaryDirectory() as tmp_dir:
            fake_profiles_path = Path(tmp_dir) / ".config/g502-profiles.json"
            fake_profiles_path.parent.mkdir(parents=True, exist_ok=True)
            repo = JsonProfileRepository(file_path=fake_profiles_path)
            manager = ProfileManager(repository=repo)
            manager.create_profile("Isolated Test Profile", "steam:12345")

            export_file = Path(tmp_dir) / "exported_test.json"
            # Export exitoso
            test_argv_export = ["g502", "export", str(export_file)]
            with patch.dict(os.environ, {"HOME": tmp_dir}):
                with patch("cli.get_services", return_value=(repo, manager, None, None, None)):
                    with patch.object(sys, "argv", test_argv_export):
                        exit_code_export = main()
                        self.assertEqual(exit_code_export, 0)
            self.assertTrue(export_file.exists())

            # Import exitoso
            test_argv_import = ["g502", "import", str(export_file), "--overwrite"]
            with patch.dict(os.environ, {"HOME": tmp_dir}):
                with patch("cli.get_services", return_value=(repo, manager, None, None, None)):
                    with patch.object(sys, "argv", test_argv_import):
                        exit_code_import = main()
                        self.assertEqual(exit_code_import, 0)





if __name__ == "__main__":
    unittest.main()
