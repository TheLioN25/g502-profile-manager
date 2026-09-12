"""
Módulo de aplicaciones y acciones del dominio.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Action:
    """
    Representa una capacidad o acción disponible dentro del contexto de una Application.

    Las acciones pertenecen a la Application y pueden ser referenciadas
    por múltiples perfiles asociados a ella.

    Extensiones:
    - binding_type: Tipo de asignación de hardware (ej. 'key', 'macro', 'special').
    - binding_value: Valor o tecla física a enviar (ej. '1', 'ctrl', 'alt+f4').
    """

    action_id: str
    name: str
    application_id: str
    description: str = ""
    binding_type: str = "key"
    binding_value: str = ""

    def __post_init__(self):
        if not isinstance(self.action_id, str) or not self.action_id.strip():
            raise ValueError("action_id no puede estar vacío.")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name no puede estar vacío.")
        if not isinstance(self.application_id, str) or not self.application_id.strip():
            raise ValueError("application_id no puede estar vacío.")

        b_type = (
            self.binding_type.strip()
            if isinstance(self.binding_type, str) and self.binding_type.strip()
            else "key"
        )
        b_val = (
            self.binding_value.strip()
            if isinstance(self.binding_value, str)
            else ""
        )

        object.__setattr__(self, "action_id", self.action_id.strip())
        object.__setattr__(self, "name", self.name.strip())
        object.__setattr__(self, "application_id", self.application_id.strip())
        object.__setattr__(self, "description", self.description.strip())
        object.__setattr__(self, "binding_type", b_type)
        object.__setattr__(self, "binding_value", b_val)


class Application:
    """
    Representa una aplicación o videojuego que sirve como contexto de uso.

    Es la propietaria del catálogo de acciones disponibles dentro de su entorno.
    Puede existir de forma independiente sin ningún perfil asociado.
    """

    def __init__(
        self,
        application_id: str,
        name: str,
        actions: Iterable[Action] | None = None,
    ):
        if not isinstance(application_id, str) or not application_id.strip():
            raise ValueError("application_id no puede estar vacío.")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("name no puede estar vacío.")

        self._application_id: str = application_id.strip()
        self._name: str = name.strip()
        self._actions: dict[str, Action] = {}

        if actions:
            for action in actions:
                self.add_action(action)

    @property
    def application_id(self) -> str:
        """Identificador único del contexto (ej. 'steam:230410')."""
        return self._application_id

    @property
    def name(self) -> str:
        """Nombre amigable de la aplicación (ej. 'Warframe')."""
        return self._name

    def change_name(self, new_name: str) -> None:
        """Modifica el nombre legible de la aplicación."""
        if not isinstance(new_name, str) or not new_name.strip():
            raise ValueError("El nombre no puede estar vacío.")
        self._name = new_name.strip()

    def add_action(self, action: Action) -> None:
        """
        Registra una acción disponible en esta aplicación.

        Asegura que la acción pertenezca al mismo contexto.
        """
        if not isinstance(action, Action):
            raise TypeError("action debe ser una instancia de Action.")
        if action.application_id != self._application_id:
            raise ValueError(
                f"No se puede agregar una acción perteneciente a '{action.application_id}' "
                f"en la aplicación '{self._application_id}'."
            )
        self._actions[action.action_id] = action

    def get_action(self, action_id: str) -> Action | None:
        """Busca una acción por su ID."""
        if not isinstance(action_id, str):
            return None
        return self._actions.get(action_id.strip())

    def has_action(self, action_id: str) -> bool:
        """Comprueba si una acción está registrada."""
        if not isinstance(action_id, str):
            return False
        return action_id.strip() in self._actions

    def list_actions(self) -> tuple[Action, ...]:
        """Devuelve una tupla inmutable con todas las acciones registradas."""
        return tuple(self._actions.values())
