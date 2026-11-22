"""
Pruebas unitarias para la entidad Application.
"""

from dataclasses import FrozenInstanceError
from pathlib import Path
import sys
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
            binding_type="key",
            binding_value="1",
        )
        app.add_action(act)

        self.assertTrue(app.has_action("ability_1"))
        self.assertEqual(app.get_action("ability_1"), act)
        self.assertEqual(act.binding_type, "key")
        self.assertEqual(act.binding_value, "1")
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

    def test_action_is_immutable(self) -> None:
        """[M-01] Verifica que Action sea una dataclass inmutable (frozen=True)."""
        act = Action(
            action_id="attack",
            name="Ataque Primario",
            application_id="steam:230410",
        )
        with self.assertRaises(FrozenInstanceError):
            act.name = "Modificado"  # type: ignore

    def test_action_binding_type_and_category_fallbacks(self) -> None:
        """
        [M-02] Verifica que un binding_type vacío o no-string haga fallback seguro a 'key'
        (evaluando estrictamente la conjunción 'isinstance and strip()', evitando pop o asignaciones vacías por 'or').
        """
        # Cadena vacía debe hacer fallback a 'key'
        act_empty = Action(
            action_id="test_empty",
            name="Test Empty",
            application_id="app_1",
            binding_type="",
        )
        self.assertEqual(act_empty.binding_type, "key")

        # Cadena de solo espacios debe hacer fallback a 'key'
        act_spaces = Action(
            action_id="test_spaces",
            name="Test Spaces",
            application_id="app_1",
            binding_type="   ",
        )
        self.assertEqual(act_spaces.binding_type, "key")

        # Tipo no-string (None) debe hacer fallback seguro a 'key' sin lanzar AttributeError
        act_none = Action(
            action_id="test_none",
            name="Test None",
            application_id="app_1",
            binding_type=None,  # type: ignore
        )
        self.assertEqual(act_none.binding_type, "key")

        # Fallback de categoría vacía hacia 'General'
        act_cat = Action(
            action_id="test_cat",
            name="Test Cat",
            application_id="app_1",
            category="   ",
        )
        self.assertEqual(act_cat.category, "General")


if __name__ == "__main__":
    unittest.main()
