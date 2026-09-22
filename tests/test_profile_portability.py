import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from domain import Action, Button, DpiConfiguration, Profile
from services import ProfileManager
from storage.profile_repository import JsonProfileRepository
from cli import cmd_export, cmd_import, create_parser


class TestProfilePortability(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_file = Path(self.temp_dir.name) / "test_profiles.json"
        self.repo = JsonProfileRepository(self.repo_file)
        self.manager = ProfileManager(self.repo)

        # Crear perfiles de prueba
        self.prof1 = Profile("Warframe Solo", "steam:230410", DpiConfiguration(1200, 400), "#FF0000")
        self.prof1.assign(Button("G4", "Atrás"), Action("wf_roll", "Rodar", "steam:230410", binding_type="key", binding_value="shift"))
        self.repo.save(self.prof1)
        self.repo.set_default_profile_id("steam:230410", self.prof1.id)

        self.prof2 = Profile("Warframe Raid", "steam:230410", DpiConfiguration(1600), "#00FF00")
        self.repo.save(self.prof2)

        self.prof3 = Profile("GW2 WvW", "steam:1284210", DpiConfiguration(1000), "#0000FF")
        self.repo.save(self.prof3)
        self.repo.set_default_profile_id("steam:1284210", self.prof3.id)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_export_data_all_profiles(self):
        data = self.repo.export_data()
        self.assertEqual(data["version"], 1)
        self.assertIn("exported_at", data)
        self.assertEqual(len(data["profiles"]), 3)
        self.assertEqual(len(data["default_profiles"]), 2)
        self.assertEqual(data["default_profiles"]["steam:230410"], self.prof1.id)
        self.assertEqual(data["default_profiles"]["steam:1284210"], self.prof3.id)

    def test_export_data_filtered_by_application(self):
        data = self.repo.export_data("steam:230410")
        self.assertEqual(len(data["profiles"]), 2)
        self.assertEqual(len(data["default_profiles"]), 1)
        self.assertEqual(data["default_profiles"]["steam:230410"], self.prof1.id)
        for p in data["profiles"]:
            self.assertEqual(p["application_id"], "steam:230410")

    def test_import_data_into_clean_repository(self):
        export_data = self.repo.export_data()

        clean_file = Path(self.temp_dir.name) / "clean_profiles.json"
        clean_repo = JsonProfileRepository(clean_file)

        imported, skipped = clean_repo.import_data(export_data)
        self.assertEqual(imported, 3)
        self.assertEqual(skipped, 0)
        self.assertEqual(len(clean_repo.list_all()), 3)

        # Verificar integridad del perfil importado con asignación
        imported_wf = clean_repo.get_by_id(self.prof1.id)
        self.assertIsNotNone(imported_wf)
        self.assertEqual(imported_wf.name, "Warframe Solo")
        self.assertEqual(imported_wf.dpi.dpi, 1200)
        self.assertEqual(imported_wf.dpi.shift_dpi, 400)
        self.assertEqual(imported_wf.led_color, "#FF0000")
        self.assertEqual(len(imported_wf.list_assignments()), 1)
        self.assertEqual(imported_wf.list_assignments()[0].button.button_id, "G4")
        self.assertEqual(imported_wf.list_assignments()[0].action.binding_value, "shift")
        self.assertEqual(clean_repo.get_default_profile_id("steam:230410"), self.prof1.id)

    def test_import_data_duplicate_skip(self):
        export_data = self.repo.export_data()

        # Importar de nuevo en el mismo repositorio sin sobrescribir
        imported, skipped = self.repo.import_data(export_data, overwrite=False)
        self.assertEqual(imported, 0)
        self.assertEqual(skipped, 3)

    def test_import_data_duplicate_overwrite(self):
        export_data = self.repo.export_data()

        # Modificar un perfil en los datos exportados
        export_data["profiles"][0]["name"] = "Warframe Modificado"

        imported, skipped = self.repo.import_data(export_data, overwrite=True)
        self.assertEqual(imported, 3)
        self.assertEqual(skipped, 0)

        modified_prof = self.repo.get_by_id(export_data["profiles"][0]["id"])
        self.assertEqual(modified_prof.name, "Warframe Modificado")

    def test_import_data_resilience_malformed_entries(self):
        corrupted_data = {
            "version": 1,
            "profiles": [
                "esto no es un dict",
                {"name": "Incompleto"},  # Falta application_id, id, etc.
            ]
        }
        imported, skipped = self.repo.import_data(corrupted_data)
        self.assertEqual(imported, 0)
        self.assertEqual(skipped, 2)

    def test_manager_export_and_import_files(self):
        target_json = Path(self.temp_dir.name) / "backup.json"
        count = self.manager.export_to_file(target_json)
        self.assertEqual(count, 3)
        self.assertTrue(target_json.exists())

        # Crear nuevo manager con repositorio vacío
        new_repo_file = Path(self.temp_dir.name) / "migrated.json"
        new_repo = JsonProfileRepository(new_repo_file)
        new_manager = ProfileManager(new_repo)

        imported, skipped = new_manager.import_from_file(target_json)
        self.assertEqual(imported, 3)
        self.assertEqual(skipped, 0)
        self.assertEqual(len(new_repo.list_all()), 3)

    def test_cli_export_and_import(self):
        parser = create_parser()
        export_file = Path(self.temp_dir.name) / "cli_backup.json"

        # Simular CLI export
        args_export = parser.parse_args(["export", str(export_file), "--app", "steam:230410"])
        with patch("cli.get_services") as mock_services:
            mock_services.return_value = (self.repo, self.manager, None, None, None)
            cmd_export(args_export)

        self.assertTrue(export_file.exists())
        with open(export_file, "r", encoding="utf-8") as f:
            content = json.load(f)
            self.assertEqual(len(content["profiles"]), 2)

        # Simular CLI import
        args_import = parser.parse_args(["import", str(export_file), "--overwrite"])
        with patch("cli.get_services") as mock_services:
            mock_services.return_value = (self.repo, self.manager, None, None, None)
            cmd_import(args_import)


if __name__ == "__main__":
    unittest.main()
