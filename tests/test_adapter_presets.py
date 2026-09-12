"""
Pruebas unitarias para el catálogo de Action Presets.
"""

from pathlib import Path
import sys
import unittest

src_path = Path(__file__).resolve().parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from adapters import (
    get_preset_actions_for_application,
    populate_application_actions,
)
from domain import Application


class TestActionPresets(unittest.TestCase):
    def test_get_preset_actions_warframe(self):
        wf_actions = get_preset_actions_for_application("steam:230410")
        self.assertGreater(len(wf_actions), 0)

        action_ids = {a.action_id for a in wf_actions}
        self.assertIn("wf_ability_1", action_ids)
        self.assertIn("wf_crouch", action_ids)

        ability_1 = next(a for a in wf_actions if a.action_id == "wf_ability_1")
        self.assertEqual(ability_1.binding_type, "key")
        self.assertEqual(ability_1.binding_value, "1")

    def test_get_preset_actions_gw2(self):
        gw2_actions = get_preset_actions_for_application("steam:1284210")
        self.assertGreater(len(gw2_actions), 0)

        action_ids = {a.action_id for a in gw2_actions}
        self.assertIn("gw2_dodge", action_ids)
        self.assertIn("gw2_heal", action_ids)

    def test_populate_application_actions(self):
        app = Application("steam:230410", "Warframe")
        self.assertEqual(len(app.list_actions()), 0)

        added = populate_application_actions(app)
        self.assertGreater(added, 0)
        self.assertEqual(len(app.list_actions()), added)

        # Si volvemos a poblar, no debe duplicar
        second_run = populate_application_actions(app)
        self.assertEqual(second_run, 0)


if __name__ == "__main__":
    unittest.main()
