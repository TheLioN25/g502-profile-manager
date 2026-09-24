"""
Pruebas unitarias para JsonProfileRepository.
"""

import sys
import tempfile
from pathlib import Path
import unittest

src_path = Path(__file__).resolve().parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from domain import Action, Button, DpiConfiguration, Profile
from storage import JsonProfileRepository


class TestJsonProfileRepository(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.file_path = Path(self.temp_dir.name) / "profiles.json"
        self.repo = JsonProfileRepository(self.file_path)

        self.app_id = "steam:230410"
        self.profile = Profile(
            name="Saryn DPS",
            application_id=self.app_id,
            dpi=DpiConfiguration(1600, shift_dpi=400),
            led_color="#00E5FF",
            profile_id="p-1234",
        )
        self.btn_g5 = Button("G5", "G5 Button")
        self.action_1 = Action(
            "habilidad_1",
            "Habilidad 1",
            self.app_id,
            binding_type="key",
            binding_value="1",
        )
        self.profile.assign(self.btn_g5, self.action_1)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_save_and_retrieve_profile(self):
        self.repo.save(self.profile)

        retrieved = self.repo.get_by_id("p-1234")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "Saryn DPS")
        self.assertEqual(retrieved.application_id, self.app_id)
        self.assertEqual(retrieved.dpi.dpi, 1600)
        self.assertEqual(retrieved.dpi.shift_dpi, 400)
        self.assertEqual(retrieved.led_color, "#00E5FF")
        self.assertEqual(retrieved.led_mode, "on")
        self.assertIsNone(retrieved.led_duration)
        self.assertIsNotNone(retrieved.created_at)
        self.assertIsNotNone(retrieved.updated_at)
        self.assertEqual(len(retrieved.list_assignments()), 1)

        assignment = retrieved.get_assignment_for_button(self.btn_g5)
        self.assertIsNotNone(assignment)
        self.assertEqual(assignment.button.button_id, "G5")
        self.assertEqual(assignment.action.action_id, "habilidad_1")
        self.assertEqual(assignment.action.binding_type, "key")
        self.assertEqual(assignment.action.binding_value, "1")

    def test_save_and_retrieve_custom_led_mode(self):
        p_breathe = Profile(
            name="Breathing RGB",
            application_id=self.app_id,
            dpi=DpiConfiguration(2400),
            led_color="#5500DD",
            led_mode="breathing",
            led_duration=3000,
            profile_id="p-breathe",
        )
        self.repo.save(p_breathe)

        loaded = self.repo.get_by_id("p-breathe")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.led_mode, "breathing")
        self.assertEqual(loaded.led_duration, 3000)
        self.assertEqual(loaded.led_color, "#5500DD")


    def test_persistence_across_instances(self):
        """Comprueba que una nueva instancia cargue exactamente los datos guardados en disco."""
        self.repo.save(self.profile)

        new_repo = JsonProfileRepository(self.file_path)
        retrieved = new_repo.get_by_id("p-1234")

        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "Saryn DPS")
        self.assertEqual(len(retrieved.list_assignments()), 1)

    def test_get_by_application(self):
        p2 = Profile(
            name="Mesa Peacemaker",
            application_id=self.app_id,
            dpi=800,
            profile_id="p-5678",
        )
        p_other = Profile(
            name="Blender General",
            application_id="desktop:blender",
            dpi=1000,
            profile_id="p-9999",
        )
        self.repo.save(self.profile)
        self.repo.save(p2)
        self.repo.save(p_other)

        wf_profiles = self.repo.get_by_application(self.app_id)
        self.assertEqual(len(wf_profiles), 2)
        ids = {p.id for p in wf_profiles}
        self.assertEqual(ids, {"p-1234", "p-5678"})

    def test_default_profile_management(self):
        self.repo.save(self.profile)
        self.assertIsNone(self.repo.get_default_profile_id(self.app_id))

        self.repo.set_default_profile_id(self.app_id, "p-1234")
        self.assertEqual(self.repo.get_default_profile_id(self.app_id), "p-1234")

        # Comprobar persistencia del default en nueva instancia
        new_repo = JsonProfileRepository(self.file_path)
        self.assertEqual(new_repo.get_default_profile_id(self.app_id), "p-1234")

    def test_set_default_profile_non_existent_fails(self):
        with self.assertRaises(ValueError):
            self.repo.set_default_profile_id(self.app_id, "inexistente")

    def test_set_default_profile_wrong_application_fails(self):
        p_blender = Profile(
            name="Blender",
            application_id="desktop:blender",
            profile_id="p-blender",
        )
        self.repo.save(p_blender)

        with self.assertRaises(ValueError):
            self.repo.set_default_profile_id(self.app_id, "p-blender")

    def test_dynamic_reload_on_external_modification(self):
        self.repo.save(self.profile)

        # Simular otro proceso modificando el archivo JSON externamente
        other_repo = JsonProfileRepository(self.file_path)
        external_profile = Profile(
            name="External Update",
            application_id=self.app_id,
            dpi=1600,
            profile_id="p-ext-99",
        )
        other_repo.save(external_profile)

        # La instancia original self.repo debe detectar el cambio y recargar
        fetched = self.repo.get_by_id("p-ext-99")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.name, "External Update")


    def test_delete_profile_removes_from_repository_and_default(self):
        self.repo.save(self.profile)
        self.repo.set_default_profile_id(self.app_id, self.profile.id)
        self.assertEqual(self.repo.get_default_profile_id(self.app_id), self.profile.id)

        # Eliminar
        deleted = self.repo.delete(self.profile.id)
        self.assertTrue(deleted)
        self.assertIsNone(self.repo.get_by_id(self.profile.id))
        self.assertIsNone(self.repo.get_default_profile_id(self.app_id))

        # Intentar eliminar de nuevo debe retornar False
        self.assertFalse(self.repo.delete(self.profile.id))
        self.assertFalse(self.repo.delete("id_inexistente"))


if __name__ == "__main__":
    unittest.main()

