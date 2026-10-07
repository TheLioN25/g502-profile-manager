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
from domain import Action, Button, DpiConfiguration, Profile, G502_VARIANTS, DEFAULT_VARIANT


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

    def test_build_button_command_modifiers_vs_macros(self):
        adapter = RatbagDeviceAdapter()
        
        # 1. Modificador LeftShift (debe usar 'key' para hold y evitar error -22 en hidpp20)
        action_shift = Action(
            action_id="sprint",
            name="Acelerar",
            application_id="app",
            binding_type="key",
            binding_value="leftshift",
        )
        cmd_shift = adapter.build_button_command("dev", "G4", action_shift, slot=0)
        self.assertEqual(cmd_shift, ["ratbagctl", "dev", "profile", "0", "button", "3", "action", "set", "key", "KEY_LEFTSHIFT"])

        # 2. Modificador LeftCtrl
        action_ctrl = Action(
            action_id="crouch",
            name="Agacharse",
            application_id="app",
            binding_type="key",
            binding_value="leftctrl",
        )
        cmd_ctrl = adapter.build_button_command("dev", "G4", action_ctrl, slot=0)
        self.assertEqual(cmd_ctrl, ["ratbagctl", "dev", "profile", "0", "button", "3", "action", "set", "key", "KEY_LEFTCTRL"])

        # 4. Tecla de puntuación '.' (debe convertirse en KEY_DOT y usar 'macro' para disparar evento en juegos)
        action_dot = Action(
            action_id="dot_key",
            name="Tecla .",
            application_id="app",
            binding_type="key",
            binding_value=".",
        )
        cmd_dot = adapter.build_button_command("dev", "G4", action_dot, slot=0)
        self.assertEqual(cmd_dot, ["ratbagctl", "dev", "profile", "0", "button", "3", "action", "set", "macro", "KEY_DOT"])

        # 3. Tecla estándar (debe usar 'macro' para forzar modifiers=0 y garantizar recepción en DirectInput/Proton)
        action_regular = Action(
            action_id="skill",
            name="Habilidad 1",
            application_id="app",
            binding_type="key",
            binding_value="1",
        )
        cmd_reg = adapter.build_button_command("dev", "G5", action_regular, slot=0)
        self.assertEqual(cmd_reg, ["ratbagctl", "dev", "profile", "0", "button", "4", "action", "set", "macro", "KEY_1"])

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
        self.assertIn("ratbagctl --nocommit warbling-mara profile 0 button 4 action set macro KEY_1", flattened)
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
        self.assertIn("ratbagctl --nocommit warbling-mara profile 0 button 4 action set macro KEY_1", flattened_default)
        self.assertIn("ratbagctl --nocommit warbling-mara profile 0 button 5 action set special resolution-alternate", flattened_default)
        self.assertIn("ratbagctl warbling-mara profile active set 0", flattened_default)



    def test_find_device_regex_matching_without_target(self):
        def mock_runner(cmd: list[str]) -> subprocess.CompletedProcess:
            if cmd == ["ratbagctl", "list"]:
                stdout = "warbling-mara: Logitech G502 LIGHTSPEED Wireless Gaming Mouse\n"
                return subprocess.CompletedProcess(cmd, returncode=0, stdout=stdout, stderr="")
            return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

        adapter = RatbagDeviceAdapter(command_runner=mock_runner)
        device_id = adapter.find_device()
        self.assertEqual(device_id, "warbling-mara")

    def test_detect_device_variants_all(self):
        # 1. G502 HERO
        def mock_hero(cmd: list[str]) -> subprocess.CompletedProcess:
            if cmd == ["ratbagctl", "list"]:
                return subprocess.CompletedProcess(cmd, 0, "dev1: Logitech G502 HERO Gaming Mouse\n", "")
            return subprocess.CompletedProcess(cmd, 0, "", "")

        adapter = RatbagDeviceAdapter(command_runner=mock_hero)
        var_hero = adapter.detect_device_variant("dev1")
        self.assertEqual(var_hero, G502_VARIANTS["g502_hero"])

        # 2. G502 LIGHTSPEED
        def mock_lightspeed(cmd: list[str]) -> subprocess.CompletedProcess:
            if cmd == ["ratbagctl", "list"]:
                return subprocess.CompletedProcess(cmd, 0, "dev2: Logitech G502 LIGHTSPEED Wireless Gaming Mouse\n", "")
            return subprocess.CompletedProcess(cmd, 0, "", "")

        adapter = RatbagDeviceAdapter(command_runner=mock_lightspeed)
        var_ls = adapter.detect_device_variant("dev2")
        self.assertEqual(var_ls, G502_VARIANTS["g502_lightspeed"])
        self.assertTrue(var_ls.capabilities.has_battery)

        # 3. G502 X (sin RGB)
        def mock_x(cmd: list[str]) -> subprocess.CompletedProcess:
            if cmd == ["ratbagctl", "list"]:
                return subprocess.CompletedProcess(cmd, 0, "dev3: Logitech G502 X Gaming Mouse\n", "")
            if cmd == ["ratbagctl", "dev3", "info"]:
                return subprocess.CompletedProcess(cmd, 0, "number of leds: 0\n", "")
            return subprocess.CompletedProcess(cmd, 0, "", "")

        adapter = RatbagDeviceAdapter(command_runner=mock_x)
        var_x = adapter.detect_device_variant("dev3")
        self.assertEqual(var_x, G502_VARIANTS["g502_x"])
        self.assertFalse(var_x.capabilities.has_lighting)

        # 4. G502 X Wireless / PLUS
        def mock_x_plus(cmd: list[str]) -> subprocess.CompletedProcess:
            if cmd == ["ratbagctl", "list"]:
                return subprocess.CompletedProcess(cmd, 0, "dev4: Logitech G502 X PLUS Wireless Gaming Mouse\n", "")
            return subprocess.CompletedProcess(cmd, 0, "", "")

        adapter = RatbagDeviceAdapter(command_runner=mock_x_plus)
        var_x_plus = adapter.detect_device_variant("dev4")
        self.assertEqual(var_x_plus, G502_VARIANTS["g502_x_wireless"])
        self.assertEqual(var_x_plus.capabilities.led_zones, 8)

        # 5. Proteus Core (desambiguación por info: 1 LED)
        def mock_core(cmd: list[str]) -> subprocess.CompletedProcess:
            if cmd == ["ratbagctl", "list"]:
                return subprocess.CompletedProcess(cmd, 0, "dev5: Logitech Gaming Mouse G502\n", "")
            if cmd == ["ratbagctl", "dev5", "info"]:
                return subprocess.CompletedProcess(cmd, 0, "Profile 0:\n  number of leds: 1\n  max dpi: 12000\n", "")
            return subprocess.CompletedProcess(cmd, 0, "", "")

        adapter = RatbagDeviceAdapter(command_runner=mock_core)
        var_core = adapter.detect_device_variant("dev5")
        self.assertEqual(var_core, G502_VARIANTS["g502_proteus_core"])
        self.assertEqual(var_core.capabilities.max_dpi, 12000)

        # 6. Proteus Spectrum (desambiguación por info: 2 LEDs + 12000 DPI)
        def mock_spectrum(cmd: list[str]) -> subprocess.CompletedProcess:
            if cmd == ["ratbagctl", "list"]:
                return subprocess.CompletedProcess(cmd, 0, "dev6: Logitech Gaming Mouse G502\n", "")
            if cmd == ["ratbagctl", "dev6", "info"]:
                return subprocess.CompletedProcess(cmd, 0, "Profile 0:\n  number of leds: 2\n  max dpi: 12000\n", "")
            return subprocess.CompletedProcess(cmd, 0, "", "")

        adapter = RatbagDeviceAdapter(command_runner=mock_spectrum)
        var_spec = adapter.detect_device_variant("dev6")
        self.assertEqual(var_spec, G502_VARIANTS["g502_proteus_spectrum"])

    def test_get_battery_level_and_cached(self):
        info_output = """Device 'singing-porcupine'
Capabilities: dpi, profile, switchable-resolution, led, battery
Battery: 78% (discharging)
number of leds: 2
"""
        def mock_runner(cmd: list[str]) -> subprocess.CompletedProcess:
            if cmd == ["ratbagctl", "singing-porcupine", "info"]:
                return subprocess.CompletedProcess(cmd, 0, info_output, "")
            return subprocess.CompletedProcess(cmd, 1, "", "error")

        adapter = RatbagDeviceAdapter(command_runner=mock_runner)
        level = adapter.get_battery_level("singing-porcupine")
        self.assertEqual(level, 78)

        # Prueba de caché diferido
        cached = adapter.get_cached_battery_level("singing-porcupine", ttl_seconds=60.0)
        self.assertEqual(cached, 78)

        # Dispositivo sin batería
        self.assertIsNone(adapter.get_battery_level("cable-device"))

    def test_apply_profile_dpi_clamping_and_variant_lighting(self):
        executed_commands = []

        def mock_runner(cmd: list[str]) -> subprocess.CompletedProcess:
            executed_commands.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, "", "")

        adapter = RatbagDeviceAdapter(command_runner=mock_runner)

        # Perfil con 16.000 DPI (superior al sensor de Proteus Core que es 12.000)
        profile_high_dpi = Profile(
            name="High DPI",
            application_id="app",
            dpi=DpiConfiguration(16000),
            led_color="#00FFCC",
            led_mode="on",
        )

        # 1. Aplicar a Proteus Core: debe clampear a 12.000 DPI y no mandar hex color RGB
        core_variant = G502_VARIANTS["g502_proteus_core"]
        success = adapter.apply_profile("dev_core", profile_high_dpi, slot=0, variant=core_variant)
        self.assertTrue(success)

        flattened = [" ".join(cmd) for cmd in executed_commands]
        # DPI debe estar clampeado a 12000
        self.assertIn("ratbagctl --nocommit dev_core profile 0 dpi set 12000", flattened)
        # Proteus Core solo tiene 1 LED (0) y modo 'on', sin comando de color RGB
        self.assertIn("ratbagctl --nocommit dev_core profile 0 led 0 set mode on", flattened)
        color_cmds = [c for c in flattened if "led 0 set color" in c]
        self.assertEqual(len(color_cmds), 0)

        # 2. Aplicar a G502 X (sin iluminación)
        executed_commands.clear()
        x_variant = G502_VARIANTS["g502_x"]
        success_x = adapter.apply_profile("dev_x", profile_high_dpi, slot=0, variant=x_variant)
        self.assertTrue(success_x)

        flattened_x = [" ".join(cmd) for cmd in executed_commands]
        # DPI en G502 X es hasta 25600, por lo que 16000 no se clampa
        self.assertIn("ratbagctl --nocommit dev_x profile 0 dpi set 16000", flattened_x)
        # No debe haber ningún comando de LED
        led_cmds = [c for c in flattened_x if "led" in c]
        self.assertEqual(len(led_cmds), 0)


if __name__ == "__main__":
    unittest.main()
