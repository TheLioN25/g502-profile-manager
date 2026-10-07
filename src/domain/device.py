"""
Módulo de dispositivos y controles físicos del dominio.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class DeviceCapabilities:
    """
    Capacidades de hardware de una variante de ratón.

    Inmutable y desacoplada de la interfaz gráfica.
    """

    max_dpi: int = 25600
    has_lighting: bool = True
    led_zones: int = 2
    has_rgb: bool = True
    has_battery: bool = False

    def __post_init__(self):
        if self.max_dpi <= 0:
            raise ValueError("max_dpi debe ser mayor a 0.")
        if self.led_zones < 0:
            raise ValueError("led_zones no puede ser negativo.")


@dataclass(frozen=True)
class DeviceVariant:
    """
    Definición inmutable de una variante de hardware de la familia Logitech G502.
    """

    key: str
    name: str
    short_name: str
    capabilities: DeviceCapabilities
    usb_ids: tuple[str, ...] = ()
    ratbag_names: tuple[str, ...] = ()

    def __post_init__(self):
        if not isinstance(self.key, str) or not self.key.strip():
            raise ValueError("key no puede estar vacío.")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name no puede estar vacío.")
        if not isinstance(self.short_name, str) or not self.short_name.strip():
            raise ValueError("short_name no puede estar vacío.")


G502_VARIANTS: dict[str, DeviceVariant] = {
    "g502_proteus_core": DeviceVariant(
        key="g502_proteus_core",
        name="Logitech G502 Proteus Core Gaming Mouse",
        short_name="G502 Proteus Core",
        capabilities=DeviceCapabilities(
            max_dpi=12000,
            has_lighting=True,
            led_zones=1,
            has_rgb=False,
            has_battery=False,
        ),
        usb_ids=("046d:c07d",),
        ratbag_names=("Logitech Gaming Mouse G502", "Logitech G502 Proteus Core"),
    ),
    "g502_proteus_spectrum": DeviceVariant(
        key="g502_proteus_spectrum",
        name="Logitech G502 Proteus Spectrum Optical Gaming Mouse",
        short_name="G502 Proteus Spectrum",
        capabilities=DeviceCapabilities(
            max_dpi=12000,
            has_lighting=True,
            led_zones=2,
            has_rgb=True,
            has_battery=False,
        ),
        usb_ids=("046d:c332",),
        ratbag_names=(
            "Logitech G502 Proteus Spectrum Optical Gaming Mouse",
            "Logitech G502 Proteus Spectrum",
            "Logitech Gaming Mouse G502",
        ),
    ),
    "g502_hero": DeviceVariant(
        key="g502_hero",
        name="Logitech G502 HERO Gaming Mouse",
        short_name="G502 HERO",
        capabilities=DeviceCapabilities(
            max_dpi=25600,
            has_lighting=True,
            led_zones=2,
            has_rgb=True,
            has_battery=False,
        ),
        usb_ids=("046d:c08b",),
        ratbag_names=(
            "Logitech G502 HERO Gaming Mouse",
            "Logitech G502 HERO",
            "Logitech G502 HERO SE",
        ),
    ),
    "g502_lightspeed": DeviceVariant(
        key="g502_lightspeed",
        name="Logitech G502 LIGHTSPEED Wireless Gaming Mouse",
        short_name="G502 LIGHTSPEED",
        capabilities=DeviceCapabilities(
            max_dpi=25600,
            has_lighting=True,
            led_zones=2,
            has_rgb=True,
            has_battery=True,
        ),
        usb_ids=("046d:407f", "046d:c08d"),
        ratbag_names=(
            "Logitech G502 LIGHTSPEED Wireless Gaming Mouse",
            "Logitech G502 LIGHTSPEED",
            "Logitech Lightspeed",
        ),
    ),
    "g502_x": DeviceVariant(
        key="g502_x",
        name="Logitech G502 X Gaming Mouse",
        short_name="G502 X",
        capabilities=DeviceCapabilities(
            max_dpi=25600,
            has_lighting=False,
            led_zones=0,
            has_rgb=False,
            has_battery=False,
        ),
        usb_ids=("046d:c099",),
        ratbag_names=(
            "Logitech G502 X Gaming Mouse",
            "Logitech G502 X",
        ),
    ),
    "g502_x_wireless": DeviceVariant(
        key="g502_x_wireless",
        name="Logitech G502 X PLUS / Wireless Gaming Mouse",
        short_name="G502 X Wireless / PLUS",
        capabilities=DeviceCapabilities(
            max_dpi=25600,
            has_lighting=True,
            led_zones=8,
            has_rgb=True,
            has_battery=True,
        ),
        usb_ids=("046d:c098",),
        ratbag_names=(
            "Logitech G502 X PLUS Wireless Gaming Mouse",
            "Logitech G502 X Wireless",
            "Logitech G502 X PLUS",
        ),
    ),
}

DEFAULT_VARIANT: DeviceVariant = G502_VARIANTS["g502_hero"]


def get_variant_by_key(key: str) -> DeviceVariant:
    """
    Obtiene la variante por su clave canónica o devuelve la variante HERO por defecto.
    """
    if not isinstance(key, str):
        return DEFAULT_VARIANT
    return G502_VARIANTS.get(key.strip().lower(), DEFAULT_VARIANT)


@dataclass(frozen=True)
class Button:
    """
    Representa un botón físico o control disponible en un dispositivo.

    Inmutable y desacoplado de aplicaciones o perfiles.
    """

    button_id: str
    name: str

    def __post_init__(self):
        if not isinstance(self.button_id, str) or not self.button_id.strip():
            raise ValueError("button_id no puede estar vacío.")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name no puede estar vacío.")
        object.__setattr__(self, "button_id", self.button_id.strip())
        object.__setattr__(self, "name", self.name.strip())


class Device:
    """
    Representa un dispositivo físico (ratón, teclado, gamepad, etc.)
    que aporta una colección de controles (Buttons).

    Permite que el dominio sea extensible a otros dispositivos además del G502.
    """

    def __init__(
        self,
        device_id: str,
        name: str,
        buttons: Iterable[Button] | None = None,
        variant: DeviceVariant | None = None,
    ):
        if not isinstance(device_id, str) or not device_id.strip():
            raise ValueError("device_id no puede estar vacío.")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("name no puede estar vacío.")

        self._device_id: str = device_id.strip()
        self._name: str = name.strip()
        self._buttons: dict[str, Button] = {}
        self._variant: DeviceVariant = variant if isinstance(variant, DeviceVariant) else DEFAULT_VARIANT

        if buttons:
            for button in buttons:
                self.add_button(button)

    @property
    def device_id(self) -> str:
        """Identificador único del dispositivo (ej. 'logitech:g502_hero')."""
        return self._device_id

    @property
    def name(self) -> str:
        """Nombre descriptivo del dispositivo."""
        return self._name

    @property
    def variant(self) -> DeviceVariant:
        """Variante de hardware asociada al dispositivo."""
        return self._variant

    def add_button(self, button: Button) -> None:
        """
        Registra un botón disponible en el dispositivo.
        """
        if not isinstance(button, Button):
            raise TypeError("button debe ser una instancia de Button.")
        self._buttons[button.button_id] = button

    def get_button(self, button_id: str) -> Button | None:
        """
        Busca un botón por su identificador.
        """
        if not isinstance(button_id, str):
            return None
        return self._buttons.get(button_id.strip())

    def list_buttons(self) -> tuple[Button, ...]:
        """
        Devuelve una tupla inmutable con todos los botones registrados.
        """
        return tuple(self._buttons.values())
