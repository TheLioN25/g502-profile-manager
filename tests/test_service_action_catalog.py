"""
Pruebas unitarias para ActionCatalogService y sistema de plugins de acciones.
"""

import json
from pathlib import Path
import sys
import tempfile
import unittest

src_path = Path(__file__).resolve().parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from domain import Action, Application
from services.action_catalog import ActionCatalogService


class TestActionCatalogService(unittest.TestCase):
    def setUp(self):
        self.catalog = ActionCatalogService()

    def test_load_builtin_catalogs(self):
        # Solo juegos/aplicaciones realmente presentes
        self.assertTrue(self.catalog.has_catalog("steam:230410"))  # Warframe
        self.assertTrue(self.catalog.has_catalog("steam:1284210"))  # GW2
        self.assertTrue(self.catalog.has_catalog("desktop:general"))
        # CS2 y Dota 2 eliminados por no estar instalados
        self.assertFalse(self.catalog.has_catalog("steam:730"))
        self.assertFalse(self.catalog.has_catalog("steam:570"))

    def test_get_application_name(self):
        self.assertEqual(self.catalog.get_application_name("steam:230410"), "Warframe")
        self.assertEqual(self.catalog.get_application_name("steam:1284210"), "Guild Wars 2")
        self.assertIsNone(self.catalog.get_application_name("unknown:app"))

    def test_get_actions_warframe(self):
        actions = self.catalog.get_actions_for_application("steam:230410")
        self.assertGreaterEqual(len(actions), 10)

        action_ids = [a.action_id for a in actions]
        self.assertIn("wf_ability_1", action_ids)
        self.assertIn("wf_melee", action_ids)
        self.assertIn("wf_bullet_jump", action_ids)

        melee_action = next(a for a in actions if a.action_id == "wf_melee")
        self.assertEqual(melee_action.category, "Combate")
        self.assertEqual(melee_action.binding_value, "e")

    def test_get_categories_grouping(self):
        categories = self.catalog.get_categories_for_application("steam:230410")
        self.assertIn("Habilidades", categories)
        self.assertIn("Combate", categories)
        self.assertIn("Movimiento", categories)
        self.assertIn("Interacción", categories)

        ability_names = [a.name for a in categories["Habilidades"]]
        self.assertIn("Habilidad 1", ability_names)
        self.assertIn("Habilidad 4 (Ultimate)", ability_names)

    def test_unknown_application_returns_empty(self):
        self.assertFalse(self.catalog.has_catalog("steam:999999"))
        self.assertEqual(self.catalog.get_actions_for_application("steam:999999"), ())
        self.assertEqual(self.catalog.get_categories_for_application("steam:999999"), {})

    def test_sync_with_installed_applications_dynamic_generation(self):
        # Simula un nuevo juego descargado desde Epic Games
        new_epic_game = Application(application_id="epic:Fortnite", name="Fortnite")
        self.assertFalse(self.catalog.has_catalog("epic:Fortnite"))

        newly_synced = self.catalog.sync_with_installed_applications([new_epic_game], persist=False)
        self.assertIn("epic:Fortnite", newly_synced)
        self.assertTrue(self.catalog.has_catalog("epic:Fortnite"))

        categories = self.catalog.get_categories_for_application("epic:Fortnite")
        self.assertIn("Combate", categories)
        self.assertIn("Movimiento", categories)
        self.assertIn("Habilidades", categories)

    def test_populate_application_actions(self):
        app = Application(application_id="steam:230410", name="Warframe")
        added = self.catalog.populate_application_actions(app)
        self.assertGreaterEqual(added, 10)
        self.assertTrue(app.has_action("wf_melee"))

        # Segunda llamada no debe duplicar
        added_second = self.catalog.populate_application_actions(app)
        self.assertEqual(added_second, 0)

    def test_list_supported_applications_filtered(self):
        apps = self.catalog.list_supported_applications(installed_app_ids={"steam:230410"})
        app_ids = [a["application_id"] for a in apps]
        self.assertIn("steam:230410", app_ids)
        self.assertIn("desktop:general", app_ids)
        self.assertNotIn("steam:1284210", app_ids)

    def test_aion2_catalog_and_alias_resolution(self):
        # Coincidencia con catálogo nativo
        self.assertTrue(self.catalog.has_catalog("steam:3393110"))
        self.assertEqual(self.catalog.get_application_name("steam:3393110"), "AION 2")
        
        # Coincidencia por alias directos y variantes comunes
        aliases = ["steam:261430", "desktop:aion2", "desktop:aion", "aion2", "aion", "Aion Classic"]
        for alias in aliases:
            self.assertTrue(self.catalog.has_catalog(alias), f"Fallo al resolver alias {alias}")
            actions = self.catalog.get_actions_for_application(alias)
            self.assertEqual(len(actions), 77, f"Se esperaban 77 acciones para {alias}")

        # Verificar categorías especializadas de MMORPG
        categories = self.catalog.get_categories_for_application("steam:3393110")
        self.assertIn("Combate y Fijación de Objetivos", categories)
        self.assertIn("Habilidades Principales", categories)
        self.assertIn("Habilidades Secundarias y Combos", categories)
        self.assertIn("Movimiento y Vuelo", categories)
        self.assertIn("Interacción y Consumibles", categories)
        self.assertIn("Interfaz y Menús", categories)

        # Sincronización no genera shooter actions si el juego coincide por nombre
        detected_app = Application(application_id="wine:aion_custom", name="AION 2 - Online")
        synced = self.catalog.sync_with_installed_applications([detected_app], persist=False)
        self.assertEqual(synced, [])
        self.assertTrue(self.catalog.has_catalog("wine:aion_custom"))
        actions = self.catalog.get_actions_for_application("wine:aion_custom")
        self.assertEqual(len(actions), 77)

    def test_custom_action_isolated_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            custom_catalog = ActionCatalogService(search_paths=[temp_path])

            self.assertFalse(custom_catalog.has_catalog("custom:game"))

            action = Action(
                action_id="fire_spell",
                name="Bola de Fuego",
                application_id="custom:game",
                category="Magia",
                binding_type="key",
                binding_value="f",
            )
            success = custom_catalog.register_custom_action(
                application_id="custom:game",
                action=action,
                persist_user_preset=False,
            )
            self.assertTrue(success)
            self.assertTrue(custom_catalog.has_catalog("custom:game"))

            categories = custom_catalog.get_categories_for_application("custom:game")
            self.assertIn("Magia", categories)
            self.assertEqual(categories["Magia"][0].action_id, "fire_spell")


if __name__ == "__main__":
    unittest.main()
