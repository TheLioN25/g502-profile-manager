"""
Adaptador de hardware para libratbag y ratbagctl.

Traduce las configuraciones de dominio (Profile, DPI, LED, Botones) a comandos
reales de ratbagctl sobre el ratón Logitech G502 HERO.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import time
from typing import Callable

DEFAULT_HARDWARE_STATE_FILE = Path.home() / ".config/g502-hardware-state.json" 

from domain import (
    Action,
    DeviceVariant,
    Profile,
    G502_VARIANTS,
    DEFAULT_VARIANT,
)


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

G502_DEFAULT_BUTTON_FALLBACKS: dict[str, tuple[str, str]] = {
    "LEFT": ("button", "1"),
    "RIGHT": ("button", "2"),
    "MIDDLE": ("button", "3"),
    "G4": ("button", "4"),
    "G5": ("button", "5"),
    "SNIPER": ("special", "resolution-alternate"),
    "G7": ("special", "resolution-down"),
    "G8": ("special", "resolution-up"),
    "G9": ("special", "profile-cycle-up"),
    "WHEEL_RIGHT": ("special", "wheel-right"),
    "WHEEL_LEFT": ("special", "wheel-left"),
}

KEY_TRANSLATIONS: dict[str, str] = {
    # Modificadores
    "ctrl": "KEY_LEFTCTRL",
    "leftctrl": "KEY_LEFTCTRL",
    "rightctrl": "KEY_RIGHTCTRL",
    "shift": "KEY_LEFTSHIFT",
    "leftshift": "KEY_LEFTSHIFT",
    "rightshift": "KEY_RIGHTSHIFT",
    "alt": "KEY_LEFTALT",
    "leftalt": "KEY_LEFTALT",
    "rightalt": "KEY_RIGHTALT",
    "meta": "KEY_LEFTMETA",
    "super": "KEY_LEFTMETA",
    "leftmeta": "KEY_LEFTMETA",
    "rightmeta": "KEY_RIGHTMETA",

    # Puntuación y símbolos estándar de teclado
    ".": "KEY_DOT",
    "dot": "KEY_DOT",
    "period": "KEY_DOT",
    "punto": "KEY_DOT",
    ",": "KEY_COMMA",
    "comma": "KEY_COMMA",
    "coma": "KEY_COMMA",
    "-": "KEY_MINUS",
    "minus": "KEY_MINUS",
    "menos": "KEY_MINUS",
    "dash": "KEY_MINUS",
    "=": "KEY_EQUAL",
    "equal": "KEY_EQUAL",
    "equals": "KEY_EQUAL",
    "igual": "KEY_EQUAL",
    "+": "KEY_KPPLUS",
    "plus": "KEY_KPPLUS",
    "mas": "KEY_KPPLUS",
    "/": "KEY_SLASH",
    "slash": "KEY_SLASH",
    "barra": "KEY_SLASH",
    "\\": "KEY_BACKSLASH",
    "backslash": "KEY_BACKSLASH",
    ";": "KEY_SEMICOLON",
    "semicolon": "KEY_SEMICOLON",
    "puntoycoma": "KEY_SEMICOLON",
    "ñ": "KEY_SEMICOLON",
    "'": "KEY_APOSTROPHE",
    "apostrophe": "KEY_APOSTROPHE",
    "quote": "KEY_APOSTROPHE",
    "comilla": "KEY_APOSTROPHE",
    "`": "KEY_GRAVE",
    "grave": "KEY_GRAVE",
    "backtick": "KEY_GRAVE",
    "acento": "KEY_GRAVE",
    "tilde": "KEY_GRAVE",
    "[": "KEY_LEFTBRACE",
    "leftbracket": "KEY_LEFTBRACE",
    "corcheteizq": "KEY_LEFTBRACE",
    "]": "KEY_RIGHTBRACE",
    "rightbracket": "KEY_RIGHTBRACE",
    "corcheteder": "KEY_RIGHTBRACE",

    # Control, Espacio y Navegación
    "space": "KEY_SPACE",
    " ": "KEY_SPACE",
    "espacio": "KEY_SPACE",
    "enter": "KEY_ENTER",
    "intro": "KEY_ENTER",
    "return": "KEY_ENTER",
    "tab": "KEY_TAB",
    "esc": "KEY_ESC",
    "escape": "KEY_ESC",
    "backspace": "KEY_BACKSPACE",
    "retroceso": "KEY_BACKSPACE",
    "capslock": "KEY_CAPSLOCK",
    "bloqmayus": "KEY_CAPSLOCK",
    "caps": "KEY_CAPSLOCK",
    "up": "KEY_UP",
    "arriba": "KEY_UP",
    "down": "KEY_DOWN",
    "abajo": "KEY_DOWN",
    "left": "KEY_LEFT",
    "izquierda": "KEY_LEFT",
    "right": "KEY_RIGHT",
    "derecha": "KEY_RIGHT",
    "pageup": "KEY_PAGEUP",
    "pgup": "KEY_PAGEUP",
    "repag": "KEY_PAGEUP",
    "pagedown": "KEY_PAGEDOWN",
    "pgdn": "KEY_PAGEDOWN",
    "avpag": "KEY_PAGEDOWN",
    "home": "KEY_HOME",
    "inicio": "KEY_HOME",
    "end": "KEY_END",
    "fin": "KEY_END",
    "insert": "KEY_INSERT",
    "ins": "KEY_INSERT",
    "delete": "KEY_DELETE",
    "del": "KEY_DELETE",
    "supr": "KEY_DELETE",
    "suprimir": "KEY_DELETE",
    "numlock": "KEY_NUMLOCK",
    "bloqnum": "KEY_NUMLOCK",
    "scrolllock": "KEY_SCROLLLOCK",
    "bloqdespl": "KEY_SCROLLLOCK",
    "print": "KEY_SYSRQ",
    "printscreen": "KEY_SYSRQ",
    "prtsc": "KEY_SYSRQ",
    "imprpant": "KEY_SYSRQ",
    "pause": "KEY_PAUSE",
    "pausa": "KEY_PAUSE",
}

MODIFIER_KEYCODES: set[str] = {
    "KEY_LEFTSHIFT",
    "KEY_RIGHTSHIFT",
    "KEY_LEFTCTRL",
    "KEY_RIGHTCTRL",
    "KEY_LEFTALT",
    "KEY_RIGHTALT",
    "KEY_LEFTMETA",
    "KEY_RIGHTMETA",
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


G502_DEVICE_REGEXES: tuple[re.Pattern, ...] = (
    re.compile(r"Logitech.*G502", re.IGNORECASE),
    re.compile(r"Logitech.*Lightspeed", re.IGNORECASE),
)


class RatbagDeviceAdapter:
    """
    Adaptador de hardware para comunicación con ratbagctl.
    """

    def __init__(
        self,
        command_runner: Callable[[list[str]], subprocess.CompletedProcess] = default_command_runner,
        state_cache_file: Path | str | None = DEFAULT_HARDWARE_STATE_FILE,
    ):
        self._runner = command_runner
        self._battery_cache: dict[str, tuple[float, int | None]] = {}
        self._device_state_cache: dict[str, dict] = {}
        self._variant_cache: dict[str, DeviceVariant] = {}
        # En tests o runners personalizados, desactivar persistencia automática en disco a menos que se indique
        if command_runner is not default_command_runner and state_cache_file == DEFAULT_HARDWARE_STATE_FILE:
            self._state_cache_file = None
        else:
            self._state_cache_file = Path(state_cache_file) if state_cache_file else None

        if self._state_cache_file:
            self._load_state_cache()

    def _load_state_cache(self) -> None:
        if not self._state_cache_file or not self._state_cache_file.exists():
            return
        try:
            with open(self._state_cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            loaded: dict[str, dict] = {}
            for dev, dev_data in data.get("devices", {}).items():
                loaded[dev] = {}
                if "active_slot" in dev_data:
                    loaded[dev]["active_slot"] = dev_data["active_slot"]
                for s_key, s_val in dev_data.items():
                    if s_key == "active_slot":
                        continue
                    try:
                        slot_idx = int(s_key)
                    except ValueError:
                        continue
                    btn_dict = {
                        int(b_k): tuple(b_v)
                        for b_k, b_v in s_val.get("buttons", {}).items()
                        if str(b_k).isdigit()
                    }
                    loaded[dev][slot_idx] = {
                        "dpi": s_val.get("dpi"),
                        "led_cmds": tuple(tuple(c) for c in s_val.get("led_cmds", [])),
                        "buttons": btn_dict,
                    }
            self._device_state_cache = loaded
        except Exception:
            pass

    def _save_state_cache(self) -> None:
        if not self._state_cache_file:
            return
        try:
            data = {"devices": {}}
            for dev, dev_data in self._device_state_cache.items():
                data["devices"][dev] = {}
                if "active_slot" in dev_data:
                    data["devices"][dev]["active_slot"] = dev_data["active_slot"]
                for k, v in dev_data.items():
                    if isinstance(k, int) and isinstance(v, dict):
                        data["devices"][dev][str(k)] = {
                            "dpi": v.get("dpi"),
                            "led_cmds": [list(c) for c in v.get("led_cmds", ())],
                            "buttons": {str(b_k): list(b_v) for b_k, b_v in v.get("buttons", {}).items()},
                        }
            self._state_cache_file.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._state_cache_file.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            tmp.replace(self._state_cache_file)
        except Exception:
            pass

    def invalidate_cache(self, device: str | None = None) -> None:
        """Invalida la caché del estado físico y batería del ratón."""
        if device:
            self._device_state_cache.pop(device, None)
            self._battery_cache.pop(device, None)
            self._variant_cache.pop(device, None)
        else:
            self._device_state_cache.clear()
            self._battery_cache.clear()
            self._variant_cache.clear()
        self._save_state_cache()

    def find_device(
        self, target_name: str | None = None
    ) -> str | None:
        """
        Localiza el identificador de libratbag correspondiente al dispositivo buscado
        (ej. 'warbling-mara').

        Si target_name es None, busca cualquier variante compatible de la familia Logitech G502.
        Si target_name es un string, busca por coincidencia en el nombre reportado por ratbagctl.
        """
        result = self._runner(["ratbagctl", "list"])
        if result.returncode != 0 or not result.stdout:
            return None

        for line in result.stdout.strip().splitlines():
            if ":" in line:
                dev_id, dev_name = line.split(":", 1)
                dev_id = dev_id.strip()
                dev_name = dev_name.strip()
                if target_name:
                    if target_name.casefold() in dev_name.casefold():
                        return dev_id
                else:
                    for regex in G502_DEVICE_REGEXES:
                        if regex.search(dev_name):
                            return dev_id

        return None

    def detect_device_variant(self, device: str) -> DeviceVariant:
        """
        Determina la variante exacta de la familia Logitech G502 conectada.
        Aplica una heurística en dos pasos y almacena el resultado en caché:
        1. Comprueba la denominación del modelo en 'ratbagctl list'.
        2. Si el nombre es genérico o ambiguo, consulta 'ratbagctl <device> info'
           (número de LEDs, sensor máximo) para desambiguar entre Proteus Core y Spectrum.
        """
        device_clean = device.strip()
        if device_clean in self._variant_cache:
            return self._variant_cache[device_clean]

        matched_name = ""

        # 1. Obtener el nombre descriptivo mediante 'ratbagctl list'
        list_res = self._runner(["ratbagctl", "list"])
        if list_res.returncode == 0 and list_res.stdout:
            for line in list_res.stdout.strip().splitlines():
                if ":" in line:
                    dev_id, dev_name = line.split(":", 1)
                    if dev_id.strip() == device_clean:
                        matched_name = dev_name.strip()
                        break

        matched_name_lower = matched_name.casefold()

        variant = DEFAULT_VARIANT
        # Detección directa por nombres inequívocos
        if "lightspeed" in matched_name_lower:
            variant = G502_VARIANTS["g502_lightspeed"]
        elif "g502 x" in matched_name_lower or "g502x" in matched_name_lower:
            if "wireless" in matched_name_lower or "plus" in matched_name_lower:
                variant = G502_VARIANTS["g502_x_wireless"]
            else:
                # Verificar si info reporta 8 LEDs para el modelo X Plus
                info_res = self._runner(["ratbagctl", device_clean, "info"])
                if info_res.returncode == 0 and info_res.stdout and "number of leds: 8" in info_res.stdout.casefold():
                    variant = G502_VARIANTS["g502_x_wireless"]
                else:
                    variant = G502_VARIANTS["g502_x"]
        elif "hero" in matched_name_lower:
            variant = G502_VARIANTS["g502_hero"]
        elif "proteus spectrum" in matched_name_lower or "spectrum" in matched_name_lower:
            variant = G502_VARIANTS["g502_proteus_spectrum"]
        elif "proteus core" in matched_name_lower or "core" in matched_name_lower:
            variant = G502_VARIANTS["g502_proteus_core"]
        else:
            # 2. Paso de desambiguación si el nombre es genérico (ej. 'Logitech Gaming Mouse G502')
            info_res = self._runner(["ratbagctl", device_clean, "info"])
            if info_res.returncode == 0 and info_res.stdout:
                stdout_lower = info_res.stdout.casefold()
                # Si tiene 1 LED -> Proteus Core
                if "number of leds: 1" in stdout_lower:
                    variant = G502_VARIANTS["g502_proteus_core"]
                # Si tiene 2 LEDs y sensor max 12000 -> Proteus Spectrum
                elif "number of leds: 2" in stdout_lower and "12000" in stdout_lower:
                    variant = G502_VARIANTS["g502_proteus_spectrum"]
                elif "number of leds: 8" in stdout_lower:
                    variant = G502_VARIANTS["g502_x_wireless"]
                elif "number of leds: 0" in stdout_lower:
                    variant = G502_VARIANTS["g502_x"]
                elif "g502" in matched_name_lower:
                    variant = DEFAULT_VARIANT
            elif "g502" in matched_name_lower:
                variant = DEFAULT_VARIANT

        self._variant_cache[device_clean] = variant
        return variant

    def get_battery_level(self, device: str) -> int | None:
        """
        Obtiene el porcentaje de batería actual (0..100) para dispositivos inalámbricos.
        Devuelve None si el dispositivo no posee batería, está apagado o no responde.
        """
        result = self._runner(["ratbagctl", device, "info"])
        if result.returncode == 0 and result.stdout:
            match = re.search(r"battery(?: level)?:\s*(\d+)%?", result.stdout, re.IGNORECASE)
            if match:
                try:
                    level = int(match.group(1))
                    return max(0, min(100, level))
                except ValueError:
                    pass

        # Intento de lectura secundaria con comando específico
        res_bat = self._runner(["ratbagctl", device, "battery", "get"])
        if res_bat.returncode == 0 and res_bat.stdout:
            match = re.search(r"(\d+)%?", res_bat.stdout)
            if match:
                try:
                    level = int(match.group(1))
                    return max(0, min(100, level))
                except ValueError:
                    pass

        return None

    def get_cached_battery_level(self, device: str, ttl_seconds: float = 30.0) -> int | None:
        """
        Devuelve el nivel de batería cacheado para evitar sobrecarga de llamadas a libratbag.
        Refresca el valor si han transcurrido más de ttl_seconds (por defecto 30 segundos).
        """
        now = time.time()
        if device in self._battery_cache:
            ts, val = self._battery_cache[device]
            if now - ts < ttl_seconds:
                return val

        val = self.get_battery_level(device)
        self._battery_cache[device] = (now, val)
        return val

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
        hex_color: str | None = None,
        slot: int | None = None,
        led_index: int | None = None,
        mode: str = "on",
        duration: int | None = None,
        led_count: int | None = None,
    ) -> list[list[str]]:
        """Construye los comandos para configurar modo, color y duración de las zonas LED."""
        mode_clean = mode.strip().lower() if isinstance(mode, str) else "on"
        if mode_clean not in ("on", "breathing", "cycle", "off"):
            mode_clean = "on"

        color_clean = (hex_color.lstrip("#").strip().lower()) if hex_color else ""
        has_valid_color = len(color_clean) == 6

        if led_index is not None:
            indices = [led_index]
        elif led_count is not None:
            indices = list(range(led_count))
        else:
            indices = [0, 1]  # G502 HERO posee exactamente 2 zonas: Logo 'G' (0) y DPI (1)
        commands = []
        for idx in indices:
            cmd_mode = ["ratbagctl", device]
            if slot is not None:
                cmd_mode.extend(["profile", str(slot)])
            cmd_mode.extend(["led", str(idx), "set", "mode", mode_clean])
            commands.append(cmd_mode)

            if mode_clean in ("on", "breathing") and has_valid_color:
                cmd_color = ["ratbagctl", device]
                if slot is not None:
                    cmd_color.extend(["profile", str(slot)])
                cmd_color.extend(["led", str(idx), "set", "color", color_clean])
                commands.append(cmd_color)

            if duration is not None and duration > 0 and mode_clean in ("breathing", "cycle"):
                cmd_dur = ["ratbagctl", device]
                if slot is not None:
                    cmd_dur.extend(["profile", str(slot)])
                cmd_dur.extend(["led", str(idx), "set", "duration", str(duration)])
                commands.append(cmd_dur)

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
            # Para modificadores (Shift, Ctrl, Alt, Meta), el driver hidpp20 de libratbag
            # rechaza 'macro <KEY>' con error -22 (EINVAL) al escribir en la EEPROM del ratón.
            # Además, 'key' es obligatorio para permitir mantener presionada la tecla (hold)
            # al correr, acelerar en vuelo o esquivar en el juego.
            # Para teclas estándar simples (ej. 1, 2, e, r, .), se utiliza 'macro <KEY>' para
            # forzar modifiers=0, neutralizar modificadores residuales pegados (bug libratbag 0.18)
            # y garantizar que Proton/Wine y el motor del juego reciban eventos completos (down/up).
            if key_code in MODIFIER_KEYCODES:
                cmd.extend(["key", key_code])
            else:
                cmd.extend(["macro", key_code])
        elif action.binding_type == "macro" and action.binding_value:
            cmd.extend(["macro", action.binding_value])
        elif action.binding_type == "special" and action.binding_value:
            cmd.extend(["special", action.binding_value])
        elif action.binding_type == "disabled":
            cmd.extend(["disabled"])
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

    def set_led_lighting(
        self,
        device: str,
        hex_color: str | None = None,
        slot: int | None = None,
        led_index: int | None = None,
        mode: str = "on",
        duration: int | None = None,
    ) -> bool:
        """
        Configura el modo, color y duración de la iluminación LED.
        """
        commands = self.build_led_commands(
            device,
            hex_color=hex_color,
            slot=slot,
            led_index=led_index,
            mode=mode,
            duration=duration,
        )
        if not commands:
            return False

        all_success = True
        for cmd in commands:
            res = self._runner(cmd)
            if res.returncode != 0:
                all_success = False

        return all_success

    def set_led_color(
        self,
        device: str,
        hex_color: str,
        slot: int | None = None,
        led_index: int | None = None,
    ) -> bool:
        """
        Configura el color de iluminación LED en modo estático ('on').
        """
        return self.set_led_lighting(
            device=device,
            hex_color=hex_color,
            slot=slot,
            led_index=led_index,
            mode="on",
        )

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
        variant: DeviceVariant | None = None,
        diff_only: bool = False,
    ) -> bool:
        """
        Aplica integralmente un Profile de dominio al hardware:
        - Ajusta el DPI activo (clampeado dinámicamente al límite de la variante).
        - Ajusta la iluminación adaptada a las zonas y capacidades de la variante.
        - Asigna los botones físicos correspondientes y restaura los no asignados.

        Ejecución Atómica y Diferencial:
        Si diff_only=True y existe estado previo en caché, únicamente transmite
        al ratón los parámetros que difieren del perfil actual (delta), evitando
        escrituras redundantes en la EEPROM y bloqueos del sensor óptico.
        Aplica los comandos preparatorios con '--nocommit' para evitar múltiples
        escrituras en la memoria Flash/EEPROM del ratón, ejecuta el último comando
        sin '--nocommit' para consolidar los cambios en una sola escritura instantánea,
        y asegura que la ranura de hardware quede explícitamente activa en el ratón.
        """
        target_slot = slot if slot is not None else 0
        actual_variant = variant or self.detect_device_variant(device)

        # 1. Comando DPI (clampeado al sensor máximo de la variante)
        effective_dpi = min(profile.dpi.dpi, actual_variant.capabilities.max_dpi)
        dpi_cmd = self.build_dpi_command(device, effective_dpi, slot=target_slot)

        # 2. Comandos LED adaptados a capacidades de la variante
        led_commands: list[list[str]] = []
        if actual_variant.capabilities.has_lighting:
            led_mode = getattr(profile, "led_mode", "on")
            led_duration = getattr(profile, "led_duration", None)
            led_count = actual_variant.capabilities.led_zones

            # Proteus Core: monocromo azul fijo (sin RGB configurable)
            if not actual_variant.capabilities.has_rgb:
                if led_mode in ("on", "off", "breathing"):
                    led_commands.extend(
                        self.build_led_commands(
                            device,
                            hex_color=None,
                            slot=target_slot,
                            mode=led_mode,
                            duration=led_duration,
                            led_count=led_count,
                        )
                    )
            elif led_mode == "off" or profile.led_color or led_mode == "cycle":
                led_commands.extend(
                    self.build_led_commands(
                        device,
                        hex_color=profile.led_color,
                        slot=target_slot,
                        mode=led_mode,
                        duration=led_duration,
                        led_count=led_count,
                    )
                )

        # 3. Comandos de botones (Asignados y Restauración de no asignados para aislamiento total)
        assigned_button_ids = {
            assignment.button.button_id.strip().upper(): assignment.action
            for assignment in profile.list_assignments()
        }

        button_cmds_ordered: list[tuple[int, list[str]]] = []

        # Programar los botones configurados por el usuario
        for btn_id, action in assigned_button_ids.items():
            cmd = self.build_button_command(
                device=device,
                button_id=btn_id,
                action=action,
                slot=target_slot,
            )
            if cmd:
                btn_key = btn_id.strip().upper()
                btn_idx = G502_BUTTON_INDEX_MAP.get(btn_key, -1)
                button_cmds_ordered.append((btn_idx, cmd))

        # Restaurar a sus valores de fábrica los botones no asignados en este perfil
        for fallback_btn_id, (action_type, action_val) in G502_DEFAULT_BUTTON_FALLBACKS.items():
            is_assigned = fallback_btn_id in assigned_button_ids
            if fallback_btn_id == "SNIPER" and "G6" in assigned_button_ids:
                is_assigned = True
            elif fallback_btn_id == "G6" and "SNIPER" in assigned_button_ids:
                is_assigned = True

            if not is_assigned:
                btn_index = G502_BUTTON_INDEX_MAP[fallback_btn_id]
                cmd = ["ratbagctl", device]
                if target_slot is not None:
                    cmd.extend(["profile", str(target_slot)])
                cmd.extend(["button", str(btn_index), "action", "set", action_type, action_val])
                button_cmds_ordered.append((btn_index, cmd))

        cached_slot_state = self._device_state_cache.get(device, {}).get(target_slot)
        new_cached_state = {
            "dpi": effective_dpi,
            "led_cmds": tuple(tuple(c) for c in led_commands),
            "buttons": {idx: tuple(cmd) for idx, cmd in button_cmds_ordered if idx >= 0},
        }

        commands: list[list[str]] = []
        if diff_only and cached_slot_state is not None:
            # Filtrado diferencial: solo lo que cambió respecto al hardware
            if cached_slot_state.get("dpi") != effective_dpi:
                commands.append(dpi_cmd)

            if cached_slot_state.get("led_cmds") != new_cached_state["led_cmds"]:
                commands.extend(led_commands)

            cached_buttons = cached_slot_state.get("buttons", {})
            for idx, cmd in button_cmds_ordered:
                if cached_buttons.get(idx) != tuple(cmd):
                    commands.append(cmd)
        else:
            commands.append(dpi_cmd)
            commands.extend(led_commands)
            for _, cmd in button_cmds_ordered:
                commands.append(cmd)

        if not commands:
            # Sin diferencias físicas: no interrumpir el polling del ratón ni escribir en USB
            self._device_state_cache.setdefault(device, {})[target_slot] = new_cached_state
            self._device_state_cache.setdefault(device, {})["active_slot"] = target_slot
            self._save_state_cache()
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

        # 4. Asegurar que la ranura de hardware quede activa físicamente
        # Si diff_only=True y la ranura ya está activa en hardware según la caché,
        # evitamos ejecutar 'profile active set' para ahorrar ~1.5s y evitar recargas en flash
        cached_active_slot = self._device_state_cache.get(device, {}).get("active_slot")
        needs_slot_switch = (not diff_only) or (cached_active_slot != target_slot)
        if needs_slot_switch:
            if not self.switch_profile_slot(device, target_slot):
                all_success = False
            else:
                self._device_state_cache.setdefault(device, {})["active_slot"] = target_slot
        else:
            self._device_state_cache.setdefault(device, {})["active_slot"] = target_slot

        if all_success:
            self._device_state_cache.setdefault(device, {})[target_slot] = new_cached_state
            self._save_state_cache()
        else:
            # Si falló la comunicación, invalidar para forzar escritura completa futura
            if device in self._device_state_cache:
                self._device_state_cache[device].pop(target_slot, None)
            self._save_state_cache()

        return all_success
