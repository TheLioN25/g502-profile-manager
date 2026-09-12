"""
Módulo de dispositivos y controles físicos del dominio.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


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
    ):
        if not isinstance(device_id, str) or not device_id.strip():
            raise ValueError("device_id no puede estar vacío.")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("name no puede estar vacío.")

        self._device_id: str = device_id.strip()
        self._name: str = name.strip()
        self._buttons: dict[str, Button] = {}

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
