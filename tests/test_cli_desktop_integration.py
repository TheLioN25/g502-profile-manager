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

from cli import cmd_install_desktop, cmd_uninstall_desktop, create_parser


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


if __name__ == "__main__":
    unittest.main()
