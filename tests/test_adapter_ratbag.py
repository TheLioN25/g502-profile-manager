"""
Pruebas unitarias para RatbagDeviceAdapter.
"""

from pathlib import Path
import subprocess
import sys
import unittest

src_path = Path(__file__).resolve().parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from adapters import (
    RatbagDeviceAdapter,
    normalize_key_to_input_code,
)
from domain import Action, Button, DpiConfiguration, Profile


class TestRatbagDeviceAdapter(unittest.TestCase):
    def test_normalize_key_to_input_code(self):
        self.assertEqual(normalize_key_to_input_code("1"), "KEY_1")
        self.assertEqual(normalize_key_to_input_code("e"), "KEY_E")
        self.assertEqual(normalize_key_to_input_code("leftctrl"), "KEY_LEFTCTRL")
        self.assertEqual(normalize_key_to_input_code("ctrl"), "KEY_LEFTCTRL")
        self.assertEqual(normalize_key_to_input_code("KEY_SPACE"), "KEY_SPACE")

    def test_find_device(self):
        executed_commands = []

        def mock_runner(cmd: list[str]) -> subprocess.CompletedProcess:
            executed_commands.append(cmd)
            output = "warbling-mara:       Logitech G502 HERO Gaming Mouse\n"
            return subprocess.CompletedProcess(cmd, returncode=0, stdout=output, stderr="")

        adapter = RatbagDeviceAdapter(command_runner=mock_runner)
        device_id = adapter.find_device("Logitech G502 HERO Gaming Mouse")

        self.assertEqual(device_id, "warbling-mara")
        self.assertEqual(executed_commands, [["ratbagctl", "list"]])

    def test_get_active_profile_slot(self):
        def mock_runner(cmd: list[str]) -> subprocess.CompletedProcess:
            return subprocess.CompletedProcess(cmd, returncode=0, stdout="2\n", stderr="")

        adapter = RatbagDeviceAdapter(command_runner=mock_runner)
        slot = adapter.get_active_profile_slot("warbling-mara")
        self.assertEqual(slot, 2)

    def test_switch_profile_slot(self):
        executed_commands = []

        def mock_runner(cmd: list[str]) -> subprocess.CompletedProcess:
            executed_commands.append(cmd)
            return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

        adapter = RatbagDeviceAdapter(command_runner=mock_runner)
        success = adapter.switch_profile_slot("warbling-mara", 3)

        self.assertTrue(success)
        self.assertEqual(
            executed_commands,
            [["ratbagctl", "warbling-mara", "profile", "active", "set", "3"]],
        )

    def test_set_dpi(self):
        executed_commands = []

        def mock_runner(cmd: list[str]) -> subprocess.CompletedProcess:
            executed_commands.append(cmd)
            return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

        adapter = RatbagDeviceAdapter(command_runner=mock_runner)
        success = adapter.set_dpi("warbling-mara", 1600, slot=1)

        self.assertTrue(success)
        self.assertEqual(
            executed_commands,
            [["ratbagctl", "profile", "1", "dpi", "set", "1600"]],
        )

    def test_set_led_color(self):
        executed_commands = []

        def mock_runner(cmd: list[str]) -> subprocess.CompletedProcess:
            executed_commands.append(cmd)
            return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

        adapter = RatbagDeviceAdapter(command_runner=mock_runner)
        success = adapter.set_led_color("warbling-mara", "#00E5FF", slot=2, led_index=0)

        self.assertTrue(success)
        self.assertEqual(
            executed_commands,
            [
                ["ratbagctl", "profile", "2", "led", "0", "set", "mode", "on"],
                ["ratbagctl", "profile", "2", "led", "0", "set", "color", "00e5ff"],
            ],
        )

    def test_apply_profile(self):
        executed_commands = []

        def mock_runner(cmd: list[str]) -> subprocess.CompletedProcess:
            executed_commands.append(cmd)
            return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

        adapter = RatbagDeviceAdapter(command_runner=mock_runner)

        profile = Profile(
            name="Warframe Test",
            application_id="steam:230410",
            dpi=DpiConfiguration(1200),
            led_color="#00FF00",
        )
        btn_g5 = Button("G5", "G5")
        action = Action(
            action_id="ability_1",
            name="Habilidad 1",
            application_id="steam:230410",
            binding_type="key",
            binding_value="1",
        )
        profile.assign(btn_g5, action)

        success = adapter.apply_profile("warbling-mara", profile, slot=0)
        self.assertTrue(success)

        # Debe haber ejecutado DPI, LED y el botón G5 (que mapea a button 4)
        flattened = [" ".join(cmd) for cmd in executed_commands]
        self.assertIn("ratbagctl profile 0 dpi set 1200", flattened)
        self.assertIn("ratbagctl profile 0 led 0 set color 00ff00", flattened)
        self.assertIn("ratbagctl profile 0 button 4 action set key KEY_1", flattened)


if __name__ == "__main__":
    unittest.main()
