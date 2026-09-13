"""
Adaptador de hardware para libratbag y ratbagctl.

Traduce las configuraciones de dominio (Profile, DPI, LED, Botones) a comandos
reales de ratbagctl sobre el ratón Logitech G502 HERO.
"""

from __future__ import annotations

import subprocess
from typing import Callable

from domain import Action, Profile


G502_BUTTON_INDEX_MAP: dict[str, int] = {
    "LEFT": 0,
    "RIGHT": 1,
    "MIDDLE": 2,
    "G4": 3,
    "G5": 4,
    "SNIPER": 5,
    "G6": 5,
    "G7": 6,
    "G8": 7,
    "G9": 8,
    "WHEEL_RIGHT": 9,
    "WHEEL_LEFT": 10,
}

KEY_TRANSLATIONS: dict[str, str] = {
    "ctrl": "KEY_LEFTCTRL",
    "leftctrl": "KEY_LEFTCTRL",
    "shift": "KEY_LEFTSHIFT",
    "leftshift": "KEY_LEFTSHIFT",
    "alt": "KEY_LEFTALT",
    "leftalt": "KEY_LEFTALT",
    "space": "KEY_SPACE",
    "enter": "KEY_ENTER",
    "tab": "KEY_TAB",
    "esc": "KEY_ESC",
}


def normalize_key_to_input_code(key: str) -> str:
    """
    Convierte una tecla simple (ej. '1', 'e', 'leftctrl') al código linux/input-event-codes.h
    esperado por ratbagctl (ej. 'KEY_1', 'KEY_E', 'KEY_LEFTCTRL').
    """
    clean_key = key.strip().casefold()
    if clean_key.startswith("key_"):
        return clean_key.upper()

    if clean_key in KEY_TRANSLATIONS:
        return KEY_TRANSLATIONS[clean_key]

    if clean_key.isalnum():
        return f"KEY_{clean_key.upper()}"

    return f"KEY_{clean_key.upper()}"


def default_command_runner(command: list[str]) -> subprocess.CompletedProcess:
    """Ejecutor predeterminado de comandos del sistema."""
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )


class RatbagDeviceAdapter:
    """
    Adaptador de hardware para comunicación con ratbagctl.
    """

    def __init__(
        self,
        command_runner: Callable[[list[str]], subprocess.CompletedProcess] = default_command_runner,
    ):
        self._runner = command_runner

    def find_device(
        self, target_name: str = "Logitech G502 HERO Gaming Mouse"
    ) -> str | None:
        """
        Localiza el identificador de libratbag correspondiente al dispositivo buscado
        (ej. 'warbling-mara').
        """
        result = self._runner(["ratbagctl", "list"])
        if result.returncode != 0 or not result.stdout:
            return None

        for line in result.stdout.strip().splitlines():
            if ":" in line:
                dev_id, dev_name = line.split(":", 1)
                if target_name.casefold() in dev_name.casefold():
                    return dev_id.strip()

        return None

    def get_active_profile_slot(self, device: str) -> int | None:
        """
        Obtiene el índice del perfil de hardware activo en el ratón (0..4).
        """
        result = self._runner(["ratbagctl", device, "profile", "active", "get"])
        if result.returncode != 0:
            return None

        try:
            return int(result.stdout.strip())
        except ValueError:
            return None

    def switch_profile_slot(self, device: str, slot: int) -> bool:
        """
        Conmuta la ranura del perfil activo en el hardware (0..4).
        """
        result = self._runner(
            ["ratbagctl", device, "profile", "active", "set", str(slot)]
        )
        return result.returncode == 0

    def build_dpi_command(
        self, device: str, dpi: int, slot: int | None = None
    ) -> list[str]:
        """Construye el comando para configurar DPI."""
        cmd = ["ratbagctl", device]
        if slot is not None:
            cmd.extend(["profile", str(slot)])
        cmd.extend(["dpi", "set", str(dpi)])
        return cmd

    def build_led_commands(
        self,
        device: str,
        hex_color: str,
        slot: int | None = None,
        led_index: int | None = None,
    ) -> list[list[str]]:
        """Construye los comandos para configurar modo y color de las zonas LED."""
        color_clean = hex_color.lstrip("#").strip().lower()
        if len(color_clean) != 6:
            return []

        indices = (
            [led_index]
            if led_index is not None
            else [0, 1]  # G502 HERO posee exactamente 2 zonas: Logo 'G' (0) y DPI (1)
        )
        commands = []
        for idx in indices:
            cmd_mode = ["ratbagctl", device]
            if slot is not None:
                cmd_mode.extend(["profile", str(slot)])
            cmd_mode.extend(["led", str(idx), "set", "mode", "on"])
            commands.append(cmd_mode)

            cmd_color = ["ratbagctl", device]
            if slot is not None:
                cmd_color.extend(["profile", str(slot)])
            cmd_color.extend(["led", str(idx), "set", "color", color_clean])
            commands.append(cmd_color)

        return commands

    def build_button_command(
        self,
        device: str,
        button_id: str,
        action: Action,
        slot: int | None = None,
    ) -> list[str] | None:
        """Construye el comando para configurar la acción de un botón físico."""
        btn_key = button_id.strip().upper()
        if btn_key not in G502_BUTTON_INDEX_MAP:
            return None

        btn_index = G502_BUTTON_INDEX_MAP[btn_key]
        cmd = ["ratbagctl", device]
        if slot is not None:
            cmd.extend(["profile", str(slot)])

        cmd.extend(["button", str(btn_index), "action", "set"])

        if action.binding_type == "key" and action.binding_value:
            key_code = normalize_key_to_input_code(action.binding_value)
            cmd.extend(["key", key_code])
        elif action.binding_type == "macro" and action.binding_value:
            cmd.extend(["macro", action.binding_value])
        elif action.binding_type == "special" and action.binding_value:
            cmd.extend(["special", action.binding_value])
        else:
            return None

        return cmd

    def set_dpi(
        self, device: str, dpi: int, slot: int | None = None
    ) -> bool:
        """
        Ajusta el valor de DPI en el mouse.
        """
        cmd = self.build_dpi_command(device, dpi, slot=slot)
        result = self._runner(cmd)
        return result.returncode == 0

    def get_led_count(self, device: str) -> int:
        """
        Obtiene la cantidad de zonas LED configurables del dispositivo.
        """
        result = self._runner(["ratbagctl", device, "info"])
        if result.returncode == 0 and result.stdout:
            for line in result.stdout.splitlines():
                if "number of leds:" in line.casefold():
                    try:
                        return int(line.split(":")[-1].strip())
                    except ValueError:
                        pass
        return 2

    def set_led_color(
        self,
        device: str,
        hex_color: str,
        slot: int | None = None,
        led_index: int | None = None,
    ) -> bool:
        """
        Configura el color de iluminación LED en formato hexadecimal RRGGBB.
        Si led_index es None, aplica el color a todas las zonas LED del ratón
        (tanto el logo 'G' como los indicadores DPI).
        """
        commands = self.build_led_commands(device, hex_color, slot=slot, led_index=led_index)
        if not commands:
            return False

        all_success = True
        for cmd in commands:
            res = self._runner(cmd)
            if res.returncode != 0:
                all_success = False

        return all_success

    def apply_button_action(
        self,
        device: str,
        button_id: str,
        action: Action,
        slot: int | None = None,
    ) -> bool:
        """
        Configura la acción en un botón físico del ratón mediante ratbagctl.
        """
        cmd = self.build_button_command(device, button_id, action, slot=slot)
        if not cmd:
            return False

        result = self._runner(cmd)
        return result.returncode == 0

    def apply_profile(
        self,
        device: str,
        profile: Profile,
        slot: int | None = None,
    ) -> bool:
        """
        Aplica integralmente un Profile de dominio al hardware:
        - Ajusta el DPI activo.
        - Ajusta el color LED en todas las zonas.
        - Asigna los botones físicos correspondientes.

        Ejecución Atómica:
        Aplica los comandos preparatorios con '--nocommit' para evitar múltiples
        escrituras en la memoria Flash/EEPROM del ratón, y ejecuta el último comando
        sin '--nocommit' para consolidar los cambios en una sola escritura instantánea.
        """
        commands: list[list[str]] = []

        # 1. Comando DPI
        commands.append(self.build_dpi_command(device, profile.dpi.dpi, slot=slot))

        # 2. Comandos LED (Logo G + Indicadores DPI)
        if profile.led_color:
            commands.extend(self.build_led_commands(device, profile.led_color, slot=slot))

        # 3. Comandos de botones asignados
        for assignment in profile.list_assignments():
            cmd = self.build_button_command(
                device=device,
                button_id=assignment.button.button_id,
                action=assignment.action,
                slot=slot,
            )
            if cmd:
                commands.append(cmd)

        if not commands:
            return True

        all_success = True
        total = len(commands)

        for i, cmd in enumerate(commands):
            is_last = (i == total - 1)
            actual_cmd = list(cmd)
            if not is_last:
                # Flag '--nocommit' permite agrupar todas las operaciones previas
                # sin saturar la EEPROM del ratón.
                actual_cmd.insert(1, "--nocommit")

            res = self._runner(actual_cmd)
            if res.returncode != 0:
                all_success = False

        return all_success
