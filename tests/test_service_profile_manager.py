"""
Pruebas unitarias para ProfileManager.
"""

import sys
import tempfile
from pathlib import Path
import unittest

src_path = Path(__file__).resolve().parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from domain import Action, Button
from services import ProfileManager
from storage import JsonProfileRepository


class TestProfileManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.file_path = Path(self.temp_dir.name) / "profiles.json"
        self.repo = JsonProfileRepository(self.file_path)
        self.manager = ProfileManager(self.repo)

        self.app_id = "steam:230410"
        self.btn_g4 = Button("G4", "Botón G4")
        self.btn_g5 = Button("G5", "Botón G5")
        self.action_1 = Action("habilidad_1", "Habilidad 1", self.app_id)
        self.action_2 = Action("habilidad_2", "Habilidad 2", self.app_id)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_create_profile_sets_first_as_default(self):
        profile1 = self.manager.create_profile("Perfil Uno", self.app_id, 1200)

        self.assertEqual(profile1.name, "Perfil Uno")
        self.assertEqual(profile1.application_id, self.app_id)
        self.assertEqual(profile1.dpi.dpi, 1200)

        # Debe ser automáticamente el predeterminado
        default_profile = self.manager.get_default_profile(self.app_id)
        self.assertIsNotNone(default_profile)
        self.assertEqual(default_profile.id, profile1.id)

        # El segundo perfil no sobrescribe el predeterminado existente
        profile2 = self.manager.create_profile("Perfil Dos", self.app_id, 1600)
        current_default = self.manager.get_default_profile(self.app_id)
        self.assertEqual(current_default.id, profile1.id)

    def test_rename_profile(self):
        profile = self.manager.create_profile("Original", self.app_id)
        updated = self.manager.rename_profile(profile.id, "Renombrado")

        self.assertEqual(updated.name, "Renombrado")

        # Verificar persistencia en disco
        saved = self.repo.get_by_id(profile.id)
        self.assertEqual(saved.name, "Renombrado")

    def test_set_profile_dpi(self):
        profile = self.manager.create_profile("Perfil DPI", self.app_id, 800)
        updated = self.manager.set_profile_dpi(profile.id, 2400)

        self.assertEqual(updated.dpi.dpi, 2400)
        saved = self.repo.get_by_id(profile.id)
        self.assertEqual(saved.dpi.dpi, 2400)

    def test_set_profile_led_color(self):
        profile = self.manager.create_profile("Perfil LED", self.app_id, 800, led_color="#FF0000")
        self.assertEqual(profile.led_color, "#FF0000")

        updated = self.manager.set_profile_led_color(profile.id, "#00FF00")
        self.assertEqual(updated.led_color, "#00FF00")
        saved = self.repo.get_by_id(profile.id)
        self.assertEqual(saved.led_color, "#00FF00")

    def test_assign_and_unassign_button(self):
        profile = self.manager.create_profile("Perfil Asignaciones", self.app_id)

        # Asignar
        self.manager.assign_button(profile.id, self.btn_g5, self.action_1)
        saved = self.repo.get_by_id(profile.id)
        self.assertEqual(len(saved.list_assignments()), 1)
        self.assertEqual(saved.get_assignment_for_button(self.btn_g5).action, self.action_1)

        # Desasignar
        self.manager.unassign_button(profile.id, self.btn_g5)
        saved = self.repo.get_by_id(profile.id)
        self.assertIsNone(saved.get_assignment_for_button(self.btn_g5))
        self.assertEqual(len(saved.list_assignments()), 0)

    def test_reset_profile(self):
        profile = self.manager.create_profile("Perfil Para Resetear", self.app_id)
        self.manager.assign_button(profile.id, self.btn_g4, self.action_1)
        self.manager.assign_button(profile.id, self.btn_g5, self.action_2)

        saved = self.repo.get_by_id(profile.id)
        self.assertEqual(len(saved.list_assignments()), 2)

        # Resetear
        reset = self.manager.reset_profile(profile.id)
        self.assertEqual(len(reset.list_assignments()), 0)

        # Comprobar persistencia del reset
        saved_after_reset = self.repo.get_by_id(profile.id)
        self.assertEqual(len(saved_after_reset.list_assignments()), 0)
        # El perfil sigue existiendo, solo se limpiaron sus asignaciones
        self.assertEqual(saved_after_reset.name, "Perfil Para Resetear")

    def test_get_active_profile_for_application(self):
        # Caso 1: Aplicación sin perfiles
        self.assertIsNone(self.manager.get_active_profile_for_application("app:desconocida"))

        # Caso 2: Aplicación con perfiles y predeterminado explícito
        p1 = self.manager.create_profile("P1", self.app_id)
        p2 = self.manager.create_profile("P2", self.app_id)

        self.manager.set_default_profile(self.app_id, p2.id)
        active = self.manager.get_active_profile_for_application(self.app_id)
        self.assertEqual(active.id, p2.id)

    def test_operations_on_non_existent_profile_raise_error(self):
        with self.assertRaises(KeyError):
            self.manager.rename_profile("id_inexistente", "Nuevo")
        with self.assertRaises(KeyError):
            self.manager.set_profile_dpi("id_inexistente", 1200)
        with self.assertRaises(KeyError):
            self.manager.reset_profile("id_inexistente")


    def test_duplicate_profile_copies_all_settings_and_assignments(self):
        original = self.manager.create_profile("Original", self.app_id, 3200, led_color="#123456")
        self.manager.assign_button(original.id, self.btn_g5, self.action_1)

        cloned = self.manager.duplicate_profile(original.id, "Copia de Original")

        self.assertNotEqual(cloned.id, original.id)
        self.assertEqual(cloned.name, "Copia de Original")
        self.assertEqual(cloned.application_id, self.app_id)
        self.assertEqual(cloned.dpi.dpi, 3200)
        self.assertEqual(cloned.led_color, "#123456")
        self.assertEqual(len(cloned.list_assignments()), 1)
        self.assertEqual(cloned.get_assignment_for_button(self.btn_g5).action.action_id, "habilidad_1")

    def test_delete_profile_service(self):
        p = self.manager.create_profile("Por Eliminar", self.app_id)
        self.assertTrue(self.manager.delete_profile(p.id))
        self.assertIsNone(self.repo.get_by_id(p.id))


if __name__ == "__main__":
    unittest.main()
