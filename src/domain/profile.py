"""
Módulo del dominio de perfiles para G502 Profile Manager.

Contiene las entidades y objetos de valor relacionados con las preferencias
del usuario para una aplicación determinada (Profile, Assignment, DpiConfiguration).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
import uuid

from .application import Action
from .device import Button


@dataclass(frozen=True)
class DpiConfiguration:
    """
    Objeto de valor que representa la configuración de sensibilidad (DPI).

    Extensiones:
    - dpi: Sensibilidad activa principal.
    - shift_dpi: Sensibilidad temporal al mantener el botón francotirador/sniper del G502.
    """

    dpi: int
    shift_dpi: int | None = None

    MIN_DPI: int = 100
    MAX_DPI: int = 25600

    def __post_init__(self):
        if not isinstance(self.dpi, int) or isinstance(self.dpi, bool):
            raise TypeError("DPI debe ser un número entero.")
        if self.dpi < self.MIN_DPI or self.dpi > self.MAX_DPI:
            raise ValueError(
                f"DPI fuera de rango permitido [{self.MIN_DPI}, {self.MAX_DPI}]: {self.dpi}"
            )

        if self.shift_dpi is not None:
            if not isinstance(self.shift_dpi, int) or isinstance(self.shift_dpi, bool):
                raise TypeError("shift_dpi debe ser un número entero.")
            if self.shift_dpi < self.MIN_DPI or self.shift_dpi > self.MAX_DPI:
                raise ValueError(
                    f"shift_dpi fuera de rango permitido [{self.MIN_DPI}, {self.MAX_DPI}]: {self.shift_dpi}"
                )


@dataclass(frozen=True)
class Assignment:
    """
    Representa la relación entre una Action y un Button dentro de un Profile.
    """

    button: Button
    action: Action

    def __post_init__(self):
        if not isinstance(self.button, Button):
            raise TypeError("button debe ser una instancia de Button.")
        if not isinstance(self.action, Action):
            raise TypeError("action debe ser una instancia de Action.")


class Profile:
    """
    Entidad agregada que representa las preferencias de interacción del usuario
    para una aplicación determinada.

    Garantiza las invariantes de negocio:
    - 1 botón solo puede tener 1 acción a la vez.
    - 1 acción solo puede estar asignada a 1 botón a la vez dentro del mismo perfil.
    - No depende de infraestructura física ni del sistema operativo.

    Extensiones:
    - led_color: Color RGB en formato hexadecimal ('#RRGGBB') para feedback visual en el hardware.
    - created_at / updated_at: Marcas temporales ISO para trazabilidad.
    """

    def __init__(
        self,
        name: str,
        application_id: str,
        dpi: int | DpiConfiguration = 800,
        led_color: str | None = None,
        profile_id: str | None = None,
        created_at: str | None = None,
        updated_at: str | None = None,
    ):
        self._id: str = profile_id or str(uuid.uuid4())
        self._application_id: str = self._validate_application_id(application_id)
        self._name: str = ""
        self.change_name(name)

        self._dpi: DpiConfiguration = (
            dpi if isinstance(dpi, DpiConfiguration) else DpiConfiguration(dpi)
        )

        now_iso = datetime.now(timezone.utc).isoformat()
        self._created_at: str = created_at or now_iso
        self._updated_at: str = updated_at or now_iso

        self._led_color: str | None = None
        if led_color is not None:
            self.set_led_color(led_color)

        self._assignments: dict[str, Assignment] = {}

    @property
    def id(self) -> str:
        """Identificador técnico único e inmutable del perfil."""
        return self._id

    @property
    def name(self) -> str:
        """Nombre legible del perfil."""
        return self._name

    @property
    def application_id(self) -> str:
        """Identificador de la aplicación asociada a este perfil."""
        return self._application_id

    @property
    def dpi(self) -> DpiConfiguration:
        """Configuración de DPI actual del perfil."""
        return self._dpi

    @property
    def led_color(self) -> str | None:
        """Color RGB en formato '#RRGGBB', o None si no está configurado."""
        return self._led_color

    @property
    def created_at(self) -> str:
        """Marca de tiempo ISO de creación del perfil."""
        return self._created_at

    @property
    def updated_at(self) -> str:
        """Marca de tiempo ISO de la última modificación del perfil."""
        return self._updated_at

    def change_name(self, new_name: str) -> None:
        """
        Modifica el nombre del perfil, asegurando que no esté vacío.
        """
        if not isinstance(new_name, str) or not new_name.strip():
            raise ValueError("El nombre del perfil no puede estar vacío.")
        self._name = new_name.strip()
        self._touch()

    def set_dpi(self, dpi: int | DpiConfiguration) -> None:
        """
        Actualiza el valor de DPI validando los rangos admisibles.
        """
        if isinstance(dpi, DpiConfiguration):
            self._dpi = dpi
        else:
            self._dpi = DpiConfiguration(dpi)
        self._touch()

    def set_led_color(self, color: str | None) -> None:
        """
        Establece el color LED en formato '#RRGGBB' o None para deshabilitarlo.
        """
        if color is None:
            self._led_color = None
        else:
            if not isinstance(color, str):
                raise TypeError("led_color debe ser una cadena de texto.")
            color_clean = color.strip()
            if not re.match(r"^#[0-9a-fA-F]{6}$", color_clean):
                raise ValueError(
                    f"Formato de color inválido: '{color}'. Debe tener formato hexadecimal '#RRGGBB' (ej. '#00E5FF')."
                )
            self._led_color = color_clean.upper()

        self._touch()

    def assign(self, button: Button, action: Action) -> None:
        """
        Asigna una acción a un botón.

        Cumple las invariantes:
        1. Si la acción ya estaba asignada a otro botón, ese botón anterior queda libre.
        2. Si el botón ya tenía otra acción, se reemplaza.
        3. La acción debe pertenecer a la misma aplicación que el perfil.
        """
        if not isinstance(button, Button):
            raise TypeError("button debe ser una instancia de Button.")
        if not isinstance(action, Action):
            raise TypeError("action debe ser una instancia de Action.")

        if action.application_id != self._application_id:
            raise ValueError(
                f"No se puede asignar una acción de '{action.application_id}' "
                f"en un perfil perteneciente a '{self._application_id}'."
            )

        # Invariante 1: Si la acción ya estaba en otro botón, liberamos ese botón
        self.unassign_action(action)

        # Invariante 2: Asignar al nuevo botón (si tenía una acción previa, se sobrescribe)
        self._assignments[button.button_id] = Assignment(button=button, action=action)
        self._touch()

    def unassign_button(self, button: Button | str) -> bool:
        """
        Libera un botón de su acción actual.
        Devuelve True si había una asignación y se eliminó, False en caso contrario.
        """
        button_id = button.button_id if isinstance(button, Button) else button
        if button_id in self._assignments:
            del self._assignments[button_id]
            self._touch()
            return True
        return False

    def unassign_action(self, action: Action | str) -> bool:
        """
        Desvincula una acción de cualquier botón asignado dentro de este perfil.
        Devuelve True si estaba asignada y se liberó, False en caso contrario.
        """
        action_id = action.action_id if isinstance(action, Action) else action
        target_button_id: str | None = None

        for b_id, assignment in self._assignments.items():
            if assignment.action.action_id == action_id:
                target_button_id = b_id
                break

        if target_button_id is not None:
            del self._assignments[target_button_id]
            self._touch()
            return True

        return False

    def get_assignment_for_button(self, button: Button | str) -> Assignment | None:
        """
        Obtiene la asignación actual de un botón, o None si está libre.
        """
        button_id = button.button_id if isinstance(button, Button) else button
        return self._assignments.get(button_id)

    def get_button_for_action(self, action: Action | str) -> Button | None:
        """
        Obtiene el botón al que está asignada una acción, o None si no está asignada.
        """
        action_id = action.action_id if isinstance(action, Action) else action
        for assignment in self._assignments.values():
            if assignment.action.action_id == action_id:
                return assignment.button
        return None

    def list_assignments(self) -> tuple[Assignment, ...]:
        """
        Devuelve una tupla inmutable con todas las asignaciones activas.
        """
        return tuple(self._assignments.values())

    def clear_assignments(self) -> None:
        """
        Elimina todas las asignaciones activas del perfil, restableciéndolo a un estado limpio.
        """
        self._assignments.clear()
        self._touch()

    def _touch(self) -> None:
        self._updated_at = datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _validate_application_id(application_id: str) -> str:
        if not isinstance(application_id, str) or not application_id.strip():
            raise ValueError("application_id no puede estar vacío.")
        return application_id.strip()
