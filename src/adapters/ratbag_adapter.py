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

    def set_dpi(
        self, device: str, dpi: int, slot: int | None = None
    ) -> bool:
        """
        Ajusta el valor de DPI en el mouse.
        """
        cmd = ["ratbagctl"]
        if slot is not None:
            cmd.extend(["profile", str(slot)])
        cmd.extend(["dpi", "set", str(dpi)])

        result = self._runner(cmd)
        return result.returncode == 0

    def set_led_color(
        self,
        device: str,
        hex_color: str,
        slot: int | None = None,
        led_index: int = 0,
    ) -> bool:
        """
        Configura el color de iluminación LED en formato hexadecimal RRGGBB.
        """
        color_clean = hex_color.lstrip("#").strip().lower()
        if len(color_clean) != 6:
            return False

        cmd_mode = ["ratbagctl"]
        if slot is not None:
            cmd_mode.extend(["profile", str(slot)])
        cmd_mode.extend(["led", str(led_index), "set", "mode", "on"])

        cmd_color = ["ratbagctl"]
        if slot is not None:
            cmd_color.extend(["profile", str(slot)])
        cmd_color.extend(["led", str(led_index), "set", "color", color_clean])

        self._runner(cmd_mode)
        res_color = self._runner(cmd_color)
        return res_color.returncode == 0

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
        btn_key = button_id.strip().upper()
        if btn_key not in G502_BUTTON_INDEX_MAP:
            return False

        btn_index = G502_BUTTON_INDEX_MAP[btn_key]
        cmd = ["ratbagctl"]
        if slot is not None:
            cmd.extend(["profile", str(slot)])

        cmd.extend(["button", str(btn_index), "action", "set"])

        if action.binding_type == "key" and action.binding_value:
            key_code = normalize_key_to_input_code(action.binding_value)
            cmd.extend(["key", key_code])
        elif action.binding_type == "macro" and action.binding_value:
            # Soporte para macros simples o series de teclas
            cmd.extend(["macro", action.binding_value])
        elif action.binding_type == "special" and action.binding_value:
            cmd.extend(["special", action.binding_value])
        else:
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
        - Ajusta el color LED si está configurado.
        - Asigna los botones físicos correspondientes.
        """
        success = True

        # 1. Configurar DPI
        if not self.set_dpi(device, profile.dpi.dpi, slot=slot):
            success = False

        # 2. Configurar LED si está definido
        if profile.led_color:
            self.set_led_color(device, profile.led_color, slot=slot)

        # 3. Configurar botones asignados
        for assignment in profile.list_assignments():
            if not self.apply_button_action(
                device=device,
                button_id=assignment.button.button_id,
                action=assignment.action,
                slot=slot,
            ):
                success = False

        return success
