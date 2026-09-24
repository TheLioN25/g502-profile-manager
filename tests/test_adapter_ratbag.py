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
            [["ratbagctl", "warbling-mara", "profile", "1", "dpi", "set", "1600"]],
        )

    def test_get_led_count(self):
        def mock_runner(cmd: list[str]) -> subprocess.CompletedProcess:
            return subprocess.CompletedProcess(
                cmd,
                returncode=0,
                stdout="warbling-mara - Logitech G502 HERO\nNumber of Leds: 2\n",
                stderr="",
            )

        adapter = RatbagDeviceAdapter(command_runner=mock_runner)
        self.assertEqual(adapter.get_led_count("warbling-mara"), 2)

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
                ["ratbagctl", "warbling-mara", "profile", "2", "led", "0", "set", "mode", "on"],
                ["ratbagctl", "warbling-mara", "profile", "2", "led", "0", "set", "color", "00e5ff"],
            ],
        )

    def test_set_led_color_all_zones(self):
        executed_commands = []

        def mock_runner(cmd: list[str]) -> subprocess.CompletedProcess:
            executed_commands.append(cmd)
            if "info" in cmd:
                return subprocess.CompletedProcess(
                    cmd, returncode=0, stdout="Number of Leds: 2\n", stderr=""
                )
            return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

        adapter = RatbagDeviceAdapter(command_runner=mock_runner)
        success = adapter.set_led_color("warbling-mara", "#00E5FF", slot=1, led_index=None)

        self.assertTrue(success)
        flattened = [" ".join(cmd) for cmd in executed_commands]
        self.assertIn("ratbagctl warbling-mara profile 1 led 0 set color 00e5ff", flattened)
        self.assertIn("ratbagctl warbling-mara profile 1 led 1 set color 00e5ff", flattened)

    def test_build_led_commands_all_modes(self):
        adapter = RatbagDeviceAdapter()

        # 1. Modo 'on' (Estático)
        cmds_on = adapter.build_led_commands("warbling-mara", hex_color="#5500DD", mode="on", led_index=0)
        self.assertEqual(
            cmds_on,
            [
                ["ratbagctl", "warbling-mara", "led", "0", "set", "mode", "on"],
                ["ratbagctl", "warbling-mara", "led", "0", "set", "color", "5500dd"],
            ],
        )

        # 2. Modo 'breathing' (Respiración con duración)
        cmds_breathe = adapter.build_led_commands("warbling-mara", hex_color="#FF0033", mode="breathing", duration=2500, led_index=1)
        self.assertEqual(
            cmds_breathe,
            [
                ["ratbagctl", "warbling-mara", "led", "1", "set", "mode", "breathing"],
                ["ratbagctl", "warbling-mara", "led", "1", "set", "color", "ff0033"],
                ["ratbagctl", "warbling-mara", "led", "1", "set", "duration", "2500"],
            ],
        )

        # 3. Modo 'cycle' (Ciclo de espectro, no requiere color)
        cmds_cycle = adapter.build_led_commands("warbling-mara", mode="cycle", duration=4000, led_index=0)
        self.assertEqual(
            cmds_cycle,
            [
                ["ratbagctl", "warbling-mara", "led", "0", "set", "mode", "cycle"],
                ["ratbagctl", "warbling-mara", "led", "0", "set", "duration", "4000"],
            ],
        )

        # 4. Modo 'off' (Apagado)
        cmds_off = adapter.build_led_commands("warbling-mara", mode="off", led_index=0)
        self.assertEqual(
            cmds_off,
            [
                ["ratbagctl", "warbling-mara", "led", "0", "set", "mode", "off"],
            ],
        )

    def test_set_led_lighting_modes(self):
        executed_commands = []

        def mock_runner(cmd: list[str]) -> subprocess.CompletedProcess:
            executed_commands.append(cmd)
            return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

        adapter = RatbagDeviceAdapter(command_runner=mock_runner)
        success = adapter.set_led_lighting(
            "warbling-mara",
            hex_color="#5500DD",
            slot=0,
            led_index=0,
            mode="breathing",
            duration=3000,
        )
        self.assertTrue(success)
        self.assertEqual(
            executed_commands,
            [
                ["ratbagctl", "warbling-mara", "profile", "0", "led", "0", "set", "mode", "breathing"],
                ["ratbagctl", "warbling-mara", "profile", "0", "led", "0", "set", "color", "5500dd"],
                ["ratbagctl", "warbling-mara", "profile", "0", "led", "0", "set", "duration", "3000"],
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

        # Debe haber ejecutado comandos en lote atómico:
        # Los pasos intermedios llevan '--nocommit' y el último ejecuta el commit final
        flattened = [" ".join(cmd) for cmd in executed_commands]
        self.assertIn("ratbagctl --nocommit warbling-mara profile 0 dpi set 1200", flattened)
        self.assertIn("ratbagctl --nocommit warbling-mara profile 0 led 0 set color 00ff00", flattened)
        self.assertIn("ratbagctl --nocommit warbling-mara profile 0 button 4 action set key KEY_1", flattened)
        # Comprobar que los botones no asignados se restablecen a sus valores de fábrica
        self.assertIn("ratbagctl --nocommit warbling-mara profile 0 button 0 action set button 1", flattened)
        self.assertIn("ratbagctl --nocommit warbling-mara profile 0 button 1 action set button 2", flattened)
        self.assertIn("ratbagctl --nocommit warbling-mara profile 0 button 2 action set button 3", flattened)
        self.assertIn("ratbagctl --nocommit warbling-mara profile 0 button 3 action set button 4", flattened)
        self.assertIn("ratbagctl --nocommit warbling-mara profile 0 button 5 action set special resolution-alternate", flattened)
        self.assertIn("ratbagctl --nocommit warbling-mara profile 0 button 6 action set special resolution-down", flattened)
        self.assertIn("ratbagctl warbling-mara profile active set 0", flattened)

        # Si slot=None, debe por defecto dirigirse al perfil 0 del hardware
        executed_commands.clear()
        success_default = adapter.apply_profile("warbling-mara", profile, slot=None)
        self.assertTrue(success_default)
        flattened_default = [" ".join(cmd) for cmd in executed_commands]
        self.assertIn("ratbagctl --nocommit warbling-mara profile 0 dpi set 1200", flattened_default)
        self.assertIn("ratbagctl --nocommit warbling-mara profile 0 button 4 action set key KEY_1", flattened_default)
        self.assertIn("ratbagctl --nocommit warbling-mara profile 0 button 5 action set special resolution-alternate", flattened_default)
        self.assertIn("ratbagctl warbling-mara profile active set 0", flattened_default)


if __name__ == "__main__":
    unittest.main()
