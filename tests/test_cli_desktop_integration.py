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
            self.assertEqual(config["Install"]["WantedBy"], "default.target")

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


if __name__ == "__main__":
    unittest.main()
