"""
Pruebas unitarias para la capa de dominio de Profile y sus invariantes.
"""

import sys
from pathlib import Path
import unittest

# Asegurar que 'src' esté en el path de Python
src_path = Path(__file__).resolve().parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from domain import Action, Assignment, Button, DpiConfiguration, Profile


class TestDomainButton(unittest.TestCase):
    def test_valid_button_creation(self):
        btn = Button(button_id="G5", name="Botón Lateral G5")
        self.assertEqual(btn.button_id, "G5")
        self.assertEqual(btn.name, "Botón Lateral G5")

    def test_invalid_button_raises_error(self):
        with self.assertRaises(ValueError):
            Button(button_id="", name="Válido")
        with self.assertRaises(ValueError):
            Button(button_id="G5", name="   ")


class TestDomainAction(unittest.TestCase):
    def test_valid_action_creation(self):
        act = Action(
            action_id="ability_1",
            name="Habilidad 1",
            application_id="steam:230410",
            description="Lanza la primera habilidad",
        )
        self.assertEqual(act.action_id, "ability_1")
        self.assertEqual(act.name, "Habilidad 1")
        self.assertEqual(act.application_id, "steam:230410")
        self.assertEqual(act.description, "Lanza la primera habilidad")

    def test_invalid_action_raises_error(self):
        with self.assertRaises(ValueError):
            Action(action_id="", name="Acción", application_id="app_1")
        with self.assertRaises(ValueError):
            Action(action_id="act_1", name="   ", application_id="app_1")
        with self.assertRaises(ValueError):
            Action(action_id="act_1", name="Acción", application_id="")


class TestDomainDpiConfiguration(unittest.TestCase):
    def test_valid_dpi(self):
        dpi = DpiConfiguration(1600)
        self.assertEqual(dpi.dpi, 1600)

    def test_dpi_out_of_bounds(self):
        with self.assertRaises(ValueError):
            DpiConfiguration(50)  # menor a 100
        with self.assertRaises(ValueError):
            DpiConfiguration(30000)  # mayor a 25600

    def test_dpi_invalid_type(self):
        with self.assertRaises(TypeError):
            DpiConfiguration("1600")  # type: ignore
        with self.assertRaises(TypeError):
            DpiConfiguration(True)  # type: ignore


class TestDomainProfile(unittest.TestCase):
    def setUp(self):
        self.app_id = "steam:230410"
        self.profile = Profile(
            name="Saryn Principal",
            application_id=self.app_id,
            dpi=1200,
        )
        self.btn_g4 = Button(button_id="G4", name="G4")
        self.btn_g5 = Button(button_id="G5", name="G5")
        self.btn_g6 = Button(button_id="G6", name="G6")

        self.action_1 = Action(
            action_id="habilidad_1",
            name="Habilidad 1",
            application_id=self.app_id,
        )
        self.action_2 = Action(
            action_id="habilidad_2",
            name="Habilidad 2",
            application_id=self.app_id,
        )

    def test_profile_initial_state(self):
        self.assertEqual(self.profile.name, "Saryn Principal")
        self.assertEqual(self.profile.application_id, self.app_id)
        self.assertEqual(self.profile.dpi.dpi, 1200)
        self.assertIsNotNone(self.profile.id)
        self.assertEqual(len(self.profile.list_assignments()), 0)

    def test_change_name_validation(self):
        self.profile.change_name("Nuevo Nombre")
        self.assertEqual(self.profile.name, "Nuevo Nombre")

        with self.assertRaises(ValueError):
            self.profile.change_name("")
        with self.assertRaises(ValueError):
            self.profile.change_name("    ")

    def test_set_dpi(self):
        self.profile.set_dpi(2400)
        self.assertEqual(self.profile.dpi.dpi, 2400)

        with self.assertRaises(ValueError):
            self.profile.set_dpi(90)

    def test_assign_action_to_button(self):
        self.profile.assign(self.btn_g5, self.action_1)

        assignment = self.profile.get_assignment_for_button(self.btn_g5)
        self.assertIsNotNone(assignment)
        self.assertEqual(assignment.button, self.btn_g5)
        self.assertEqual(assignment.action, self.action_1)
        self.assertEqual(self.profile.get_button_for_action(self.action_1), self.btn_g5)

    def test_invariant_button_has_only_one_action(self):
        """Si se asigna otra acción al mismo botón, se reemplaza la anterior."""
        self.profile.assign(self.btn_g5, self.action_1)
        self.profile.assign(self.btn_g5, self.action_2)

        assignment = self.profile.get_assignment_for_button(self.btn_g5)
        self.assertEqual(assignment.action, self.action_2)
        # La acción 1 ya no tiene botón asignado
        self.assertIsNone(self.profile.get_button_for_action(self.action_1))
        self.assertEqual(len(self.profile.list_assignments()), 1)

    def test_invariant_action_assigned_to_only_one_button(self):
        """Si una acción se asigna a un nuevo botón, el botón anterior queda libre."""
        self.profile.assign(self.btn_g5, self.action_1)
        # Movemos la acción 1 de G5 a G6
        self.profile.assign(self.btn_g6, self.action_1)

        # G5 ahora está libre
        self.assertIsNone(self.profile.get_assignment_for_button(self.btn_g5))
        # G6 tiene la acción 1
        assignment_g6 = self.profile.get_assignment_for_button(self.btn_g6)
        self.assertIsNotNone(assignment_g6)
        self.assertEqual(assignment_g6.action, self.action_1)
        self.assertEqual(len(self.profile.list_assignments()), 1)

    def test_cannot_assign_action_from_different_application(self):
        """No se puede asignar una acción de otro juego a este perfil."""
        blender_action = Action(
            action_id="extrude",
            name="Extruir",
            application_id="desktop:blender",
        )
        with self.assertRaises(ValueError):
            self.profile.assign(self.btn_g4, blender_action)

    def test_unassign_button(self):
        self.profile.assign(self.btn_g5, self.action_1)
        self.assertTrue(self.profile.unassign_button(self.btn_g5))
        self.assertIsNone(self.profile.get_assignment_for_button(self.btn_g5))
        self.assertIsNone(self.profile.get_button_for_action(self.action_1))
        # Desasignar un botón ya libre retorna False
        self.assertFalse(self.profile.unassign_button(self.btn_g5))

    def test_unassign_action(self):
        self.profile.assign(self.btn_g5, self.action_1)
        self.assertTrue(self.profile.unassign_action(self.action_1))
        self.assertIsNone(self.profile.get_assignment_for_button(self.btn_g5))
        self.assertIsNone(self.profile.get_button_for_action(self.action_1))
        # Desasignar una acción ya libre retorna False
        self.assertFalse(self.profile.unassign_action(self.action_1))

    def test_list_assignments_immutability(self):
        self.profile.assign(self.btn_g4, self.action_1)
        self.profile.assign(self.btn_g5, self.action_2)

        assignments = self.profile.list_assignments()
        self.assertEqual(len(assignments), 2)
        self.assertIsInstance(assignments, tuple)


if __name__ == "__main__":
    unittest.main()
