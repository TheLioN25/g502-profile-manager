"""
Pruebas unitarias para la entidad Application.
"""

import sys
from pathlib import Path
import unittest

src_path = Path(__file__).resolve().parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from domain import Action, Application


class TestDomainApplication(unittest.TestCase):
    def test_valid_application_creation(self):
        app = Application(application_id="steam:230410", name="Warframe")
        self.assertEqual(app.application_id, "steam:230410")
        self.assertEqual(app.name, "Warframe")
        self.assertEqual(len(app.list_actions()), 0)

    def test_invalid_application_raises_error(self):
        with self.assertRaises(ValueError):
            Application(application_id="", name="Warframe")
        with self.assertRaises(ValueError):
            Application(application_id="steam:230410", name="   ")

    def test_change_name(self):
        app = Application(application_id="steam:230410", name="Warframe")
        app.change_name("Warframe Evolution")
        self.assertEqual(app.name, "Warframe Evolution")

        with self.assertRaises(ValueError):
            app.change_name("")

    def test_add_and_get_action(self):
        app = Application(application_id="steam:230410", name="Warframe")
        act = Action(
            action_id="ability_1",
            name="Habilidad 1",
            application_id="steam:230410",
        )
        app.add_action(act)

        self.assertTrue(app.has_action("ability_1"))
        self.assertEqual(app.get_action("ability_1"), act)
        self.assertEqual(len(app.list_actions()), 1)

    def test_cannot_add_action_from_another_application(self):
        app = Application(application_id="steam:230410", name="Warframe")
        act_blender = Action(
            action_id="render",
            name="Renderizar",
            application_id="desktop:blender",
        )
        with self.assertRaises(ValueError):
            app.add_action(act_blender)

    def test_add_invalid_action_type(self):
        app = Application(application_id="steam:230410", name="Warframe")
        with self.assertRaises(TypeError):
            app.add_action("invalido")  # type: ignore


if __name__ == "__main__":
    unittest.main()
