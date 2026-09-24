"""
Módulo de servicios de gestión de perfiles (ProfileManager).
"""

from __future__ import annotations

import json
from pathlib import Path

from domain import Action, Button, DpiConfiguration, Profile
from storage.profile_repository import ProfileRepository


class ProfileManager:
    """
    Servicio de aplicación para la orquestación y gestión del ciclo de vida de los perfiles.

    Coordina la creación, modificación, asignación de controles, restablecimiento (reset)
    y la selección de perfil activo/predeterminado para cada contexto de uso.
    """

    def __init__(self, repository: ProfileRepository):
        self._repository = repository

    def create_profile(
        self,
        name: str,
        application_id: str,
        dpi: int | DpiConfiguration = 800,
        led_color: str | None = None,
        led_mode: str = "on",
        led_duration: int | None = None,
    ) -> Profile:
        """
        Crea un nuevo perfil, lo persiste y lo establece automáticamente como
        predeterminado si es el primer perfil asociado a la aplicación.
        """
        profile = Profile(
            name=name,
            application_id=application_id,
            dpi=dpi,
            led_color=led_color,
            led_mode=led_mode,
            led_duration=led_duration,
        )

        self._repository.save(profile)

        # Si no había un perfil predeterminado para esta aplicación, este será el predeterminado
        current_default = self._repository.get_default_profile_id(application_id)
        if current_default is None:
            self._repository.set_default_profile_id(application_id, profile.id)

        return profile

    def save_profile(self, profile: Profile) -> Profile:
        """
        Persiste un perfil (nuevo o modificado) en el repositorio y lo establece
        como predeterminado si no había uno previamente configurado.
        """
        self._repository.save(profile)
        current_default = self._repository.get_default_profile_id(profile.application_id)
        if current_default is None:
            self._repository.set_default_profile_id(profile.application_id, profile.id)
        return profile

    def get_profile(self, profile_id: str) -> Profile | None:
        """
        Obtiene un perfil por su ID único.
        """
        return self._repository.get_by_id(profile_id)

    def get_profiles_for_application(
        self, application_id: str
    ) -> tuple[Profile, ...]:
        """
        Devuelve todos los perfiles asociados a una aplicación.
        """
        return self._repository.get_by_application(application_id)

    def rename_profile(self, profile_id: str, new_name: str) -> Profile:
        """
        Cambia el nombre legible de un perfil y persiste el cambio.
        """
        profile = self._get_required_profile(profile_id)
        profile.change_name(new_name)
        self._repository.save(profile)
        return profile

    def set_profile_dpi(
        self, profile_id: str, dpi: int | DpiConfiguration
    ) -> Profile:
        """
        Actualiza el DPI de un perfil y persiste el cambio.
        """
        profile = self._get_required_profile(profile_id)
        profile.set_dpi(dpi)
        self._repository.save(profile)
        return profile

    def set_profile_led_color(
        self, profile_id: str, color: str | None
    ) -> Profile:
        """
        Configura el color LED del perfil en formato '#RRGGBB' o None.
        """
        profile = self._get_required_profile(profile_id)
        profile.set_led_color(color)
        self._repository.save(profile)
        return profile

    def set_profile_led_mode(
        self, profile_id: str, mode: str, duration: int | None = None
    ) -> Profile:
        """
        Configura el modo de iluminación LED ('on', 'breathing', 'cycle', 'off')
        y su duración/velocidad opcional.
        """
        profile = self._get_required_profile(profile_id)
        profile.set_led_mode(mode, duration)
        self._repository.save(profile)
        return profile

    def assign_button(
        self, profile_id: str, button: Button, action: Action
    ) -> Profile:
        """
        Asigna una acción a un botón dentro de un perfil y persiste el cambio.
        """
        profile = self._get_required_profile(profile_id)
        profile.assign(button, action)
        self._repository.save(profile)
        return profile

    def unassign_button(
        self, profile_id: str, button: Button | str
    ) -> Profile:
        """
        Libera un botón de su asignación actual y persiste el cambio.
        """
        profile = self._get_required_profile(profile_id)
        profile.unassign_button(button)
        self._repository.save(profile)
        return profile

    def unassign_action(
        self, profile_id: str, action: Action | str
    ) -> Profile:
        """
        Desvincula una acción de cualquier botón dentro del perfil y persiste el cambio.
        """
        profile = self._get_required_profile(profile_id)
        profile.unassign_action(action)
        self._repository.save(profile)
        return profile

    def reset_profile(self, profile_id: str) -> Profile:
        """
        Restablece el perfil vaciando todas sus asignaciones (operación de limpieza en lugar de eliminar).
        """
        profile = self._get_required_profile(profile_id)
        profile.clear_assignments()
        self._repository.save(profile)
        return profile

    def duplicate_profile(self, source_profile_id: str, new_name: str) -> Profile:
        """
        Crea una copia idéntica del perfil especificado con un nuevo nombre.
        """
        source = self._get_required_profile(source_profile_id)
        clone = Profile(
            name=new_name,
            application_id=source.application_id,
            dpi=DpiConfiguration(source.dpi.dpi, source.dpi.shift_dpi),
            led_color=source.led_color,
            led_mode=source.led_mode,
            led_duration=source.led_duration,
        )
        for assignment in source.list_assignments():
            clone.assign(assignment.button, assignment.action)

        self._repository.save(clone)
        return clone

    def delete_profile(self, profile_id: str) -> bool:
        """
        Elimina de forma permanente un perfil.
        """
        return self._repository.delete(profile_id)

    def set_default_profile(self, application_id: str, profile_id: str) -> None:
        """
        Establece explícitamente el perfil predeterminado para una aplicación.
        """
        self._repository.set_default_profile_id(application_id, profile_id)

    def get_default_profile(self, application_id: str) -> Profile | None:
        """
        Devuelve la entidad Profile marcada como predeterminada para la aplicación, o None.
        """
        default_id = self._repository.get_default_profile_id(application_id)
        if default_id is None:
            return None
        return self._repository.get_by_id(default_id)

    def get_active_profile_for_application(
        self, application_id: str
    ) -> Profile | None:
        """
        Regla de selección: Determina cuál perfil debe activarse para una aplicación.

        1. Si existe un perfil predeterminado configurado, lo devuelve.
        2. Si no hay predeterminado explícito pero hay perfiles configurados, devuelve el primero.
        3. Si la aplicación no tiene ningún perfil, devuelve None.
        """
        default_profile = self.get_default_profile(application_id)
        if default_profile is not None:
            return default_profile

        profiles = self.get_profiles_for_application(application_id)
        if profiles:
            return profiles[0]

        return None

    def _get_required_profile(self, profile_id: str) -> Profile:
        profile = self._repository.get_by_id(profile_id)
        if profile is None:
            raise KeyError(f"No se encontró el perfil con ID '{profile_id}'.")
        return profile

    def export_to_file(
        self, file_path: str | Path, application_id: str | None = None
    ) -> int:
        """
        Exporta perfiles a un archivo JSON. Retorna la cantidad de perfiles exportados.
        """
        path = Path(file_path).expanduser().resolve()
        data = self._repository.export_data(application_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return len(data.get("profiles", []))

    def import_from_file(
        self, file_path: str | Path, overwrite: bool = False
    ) -> tuple[int, int]:
        """
        Importa perfiles desde un archivo JSON. Retorna (importados_o_actualizados, omitidos).
        """
        path = Path(file_path).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"El archivo '{path}' no existe o no es un archivo regular.")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return self._repository.import_data(data, overwrite=overwrite)
