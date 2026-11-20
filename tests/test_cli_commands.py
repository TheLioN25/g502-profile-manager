"""
Pruebas unitarias dedicadas para los comandos operativos del CLI (src/cli.py).
"""

from argparse import Namespace
import importlib.util
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

src_path = Path(__file__).resolve().parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

import cli
from domain import Action, DpiConfiguration, Profile


class TestCliCommands(unittest.TestCase):
    def test_cli_bootstraps_sys_path(self) -> None:
        """[M-01] Verifica que cli.py inserte su directorio en sys.path cuando no está presente."""
        src_dir_str = str(src_path)
        orig_sys_path = list(sys.path)
        cli_file = src_path / "cli.py"

        try:
            # Retirar src_dir de sys.path
            sys.path = [p for p in sys.path if p != src_dir_str]
            self.assertNotIn(src_dir_str, sys.path)

            # Cargar cli.py desde archivo sin depender de que src_dir esté en sys.path
            spec = importlib.util.spec_from_file_location("cli_bootstrap_test", cli_file)
            assert spec is not None and spec.loader is not None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Si la línea 14 de cli.py tiene 'not in', se inserta src_dir_str.
            # Si se muta a 'in', la condición es False y NO se inserta, fallando la aserción.
            self.assertIn(src_dir_str, sys.path)
        finally:
            sys.path[:] = orig_sys_path

    def test_cmd_profiles_empty_repository_hint(self) -> None:
        """[M-02, M-03] Verifica el mensaje exacto de creación cuando no hay perfiles configurados."""
        mock_repo = MagicMock()
        mock_repo.list_all.return_value = []

        with patch("cli.get_services", return_value=(mock_repo, MagicMock(), MagicMock(), MagicMock(), MagicMock())), \
             patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            cli.cmd_profiles(Namespace())
            output = mock_stdout.getvalue()

            self.assertIn("No hay perfiles configurados.", output)
            # Validación estricta de delimitadores <app_id> y <name> (mata < por > y > por <)
            self.assertIn("g502 create <app_id> <name>", output)

    def test_cmd_profiles_default_tag_accuracy(self) -> None:
        """[M-04] Verifica que la etiqueta [PREDETERMINADO] se aplique estrictamente al perfil default."""
        p_default = Profile(
            name="Default Profile",
            application_id="steam:warframe",
            dpi=DpiConfiguration(1600),
            profile_id="prof-1",
        )
        p_other = Profile(
            name="Secondary Profile",
            application_id="steam:warframe",
            dpi=DpiConfiguration(800),
            profile_id="prof-2",
        )

        mock_repo = MagicMock()
        mock_repo.list_all.return_value = [p_default, p_other]
        mock_repo.get_default_profile_id.side_effect = lambda app_id: "prof-1" if app_id == "steam:warframe" else None

        with patch("cli.get_services", return_value=(mock_repo, MagicMock(), MagicMock(), MagicMock(), MagicMock())), \
             patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            cli.cmd_profiles(Namespace())
            output = mock_stdout.getvalue()

            self.assertIn("'Default Profile' [PREDETERMINADO]", output)
            self.assertIn("'Secondary Profile'", output)
            self.assertNotIn("'Secondary Profile' [PREDETERMINADO]", output)

    def test_cmd_presets_branching_list_vs_detail(self) -> None:
        """[M-05] Verifica la bifurcación entre listado general y detalle de una aplicación específica."""
        mock_discovery = MagicMock()
        mock_discovery.discover_all_applications.return_value = []
        mock_catalog = MagicMock()
        mock_catalog.list_supported_applications.return_value = [
            {"application_id": "steam:warframe", "name": "Warframe", "action_count": 5, "description": "Ninja game"}
        ]
        real_action = Action(
            action_id="melee",
            name="Melee Attack",
            application_id="steam:warframe",
            binding_value="e",
            binding_type="key",
            description="Quick melee",
        )
        mock_catalog.get_categories_for_application.return_value = {
            "Combat": [real_action]
        }
        mock_catalog.get_application_name.return_value = "Warframe"

        services = (MagicMock(), MagicMock(), mock_discovery, MagicMock(), mock_catalog)

        # 1. Caso 'list' explícito: debe entrar a la vista general
        with patch("cli.get_services", return_value=services), \
             patch("sys.stdout", new_callable=io.StringIO) as stdout_list:
            cli.cmd_presets(Namespace(app_id="list"))
            out_list = stdout_list.getvalue()
            self.assertIn("Juegos y aplicaciones con catálogo de acciones", out_list)
            self.assertIn("[steam:warframe] Warframe", out_list)

        # 2. Caso app_id específico: debe entrar a la vista de categorías, no a la lista general
        with patch("cli.get_services", return_value=services), \
             patch("sys.stdout", new_callable=io.StringIO) as stdout_app:
            cli.cmd_presets(Namespace(app_id="steam:warframe"))
            out_app = stdout_app.getvalue()
            self.assertNotIn("Juegos y aplicaciones con catálogo de acciones", out_app)
            self.assertIn("Catálogo de acciones para 'Warframe'", out_app)
            self.assertIn("[COMBAT]", out_app)
            self.assertIn("Melee Attack", out_app)

    def test_cmd_create_success(self) -> None:
        """Verifica la invocación exitosa del comando create desde CLI."""
        mock_manager = MagicMock()
        created_profile = Profile(
            name="New Profile",
            application_id="desktop:general",
            dpi=DpiConfiguration(1200),
            profile_id="prof-new",
        )
        mock_manager.create_profile.return_value = created_profile
        mock_catalog = MagicMock()
        mock_catalog.get_actions_for_application.return_value = []

        services = (MagicMock(), mock_manager, MagicMock(), MagicMock(), mock_catalog)
        args = Namespace(name="New Profile", app_id="desktop:general", dpi=1200, shift_dpi=None, led=None)

        with patch("cli.get_services", return_value=services), \
             patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            exit_code = cli.cmd_create(args)
            self.assertEqual(exit_code, 0)
            out = mock_stdout.getvalue()
            self.assertIn("Perfil 'New Profile' creado exitosamente.", out)
            self.assertIn("ID: prof-new", out)


if __name__ == "__main__":
    unittest.main()
