"""
Módulo de almacenamiento y persistencia para perfiles.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Protocol

from domain import Action, Button, DpiConfiguration, Profile


class ProfileRepository(Protocol):
    """
    Contrato base para repositorios de perfiles.
    """

    def save(self, profile: Profile) -> None:
        """Guarda o actualiza un perfil."""
        ...

    def get_by_id(self, profile_id: str) -> Profile | None:
        """Recupera un perfil por su ID único."""
        ...

    def get_by_application(self, application_id: str) -> tuple[Profile, ...]:
        """Recupera todos los perfiles asociados a una aplicación."""
        ...

    def list_all(self) -> tuple[Profile, ...]:
        """Lista todos los perfiles guardados."""
        ...

    def get_default_profile_id(self, application_id: str) -> str | None:
        """Devuelve el ID del perfil predeterminado para una aplicación."""
        ...

    def set_default_profile_id(self, application_id: str, profile_id: str) -> None:
        """Establece el ID del perfil predeterminado para una aplicación."""
        ...

    def delete(self, profile_id: str) -> bool:
        """Elimina un perfil por su ID."""
        ...


DEFAULT_PROFILES_FILE = Path.home() / ".config/g502-profiles.json"


class JsonProfileRepository:
    """
    Implementación de persistencia local basada en archivos JSON.

    Garantiza escritura atómica para evitar corrupción de datos
    y serializa limpiamente hacia y desde entidades puras de dominio.
    """

    def __init__(self, file_path: str | Path | None = None):
        if file_path is None:
            file_path = DEFAULT_PROFILES_FILE
        self._file_path = Path(file_path).expanduser().resolve()
        self._profiles: dict[str, Profile] = {}
        self._default_profiles: dict[str, str] = {}  # application_id -> profile_id
        self._last_mtime: float = 0.0
        self._load()

    @property
    def file_path(self) -> Path:
        """Ruta al archivo JSON de persistencia."""
        return self._file_path

    def _reload_if_needed(self) -> None:
        """Recarga perfiles desde disco si otro proceso modificó el archivo."""
        if not self._file_path.exists():
            return
        try:
            mtime = self._file_path.stat().st_mtime
            if mtime > self._last_mtime:
                self._load()
        except OSError:
            pass

    def save(self, profile: Profile) -> None:
        """
        Guarda o actualiza el perfil en memoria y lo sincroniza atómicamente a disco.
        """
        if not isinstance(profile, Profile):
            raise TypeError("profile debe ser una instancia de Profile.")

        self._reload_if_needed()
        self._profiles[profile.id] = profile
        self._flush()

    def get_by_id(self, profile_id: str) -> Profile | None:
        """
        Obtiene un perfil por su ID.
        """
        if not isinstance(profile_id, str):
            return None
        self._reload_if_needed()
        return self._profiles.get(profile_id.strip())

    def get_by_application(self, application_id: str) -> tuple[Profile, ...]:
        """
        Devuelve todos los perfiles asociados a la aplicación dada.
        """
        if not isinstance(application_id, str):
            return ()

        self._reload_if_needed()
        app_id = application_id.strip().casefold()
        return tuple(
            p
            for p in self._profiles.values()
            if p.application_id.casefold() == app_id
        )

    def list_all(self) -> tuple[Profile, ...]:
        """
        Devuelve todos los perfiles almacenados.
        """
        self._reload_if_needed()
        return tuple(self._profiles.values())

    def get_default_profile_id(self, application_id: str) -> str | None:
        """
        Devuelve el ID del perfil predeterminado para una aplicación.
        """
        if not isinstance(application_id, str):
            return None
        self._reload_if_needed()
        return self._default_profiles.get(application_id.strip().casefold())

    def set_default_profile_id(self, application_id: str, profile_id: str) -> None:
        """
        Establece el ID del perfil predeterminado para una aplicación.
        """
        if not isinstance(application_id, str) or not application_id.strip():
            raise ValueError("application_id no puede estar vacío.")
        if not isinstance(profile_id, str) or not profile_id.strip():
            raise ValueError("profile_id no puede estar vacío.")

        self._reload_if_needed()
        app_id = application_id.strip().casefold()
        p_id = profile_id.strip()

        # Validar que el perfil exista y corresponda a la aplicación
        profile = self.get_by_id(p_id)
        if profile is None:
            raise ValueError(f"El perfil con ID '{p_id}' no existe en el repositorio.")
        if profile.application_id.casefold() != app_id:
            raise ValueError(
                f"El perfil '{p_id}' pertenece a '{profile.application_id}', "
                f"no a '{application_id}'."
            )

        self._default_profiles[app_id] = p_id
        self._flush()

    def delete(self, profile_id: str) -> bool:
        """
        Elimina un perfil por su ID único y actualiza el archivo atómicamente.
        """
        if not isinstance(profile_id, str):
            return False

        self._reload_if_needed()
        clean_id = profile_id.strip()
        if clean_id not in self._profiles:
            return False

        del self._profiles[clean_id]

        # Limpiar de default_profiles si correspondía
        for app_id, def_id in list(self._default_profiles.items()):
            if def_id == clean_id:
                del self._default_profiles[app_id]

        self._flush()
        return True

    def _load(self) -> None:
        """
        Carga los datos desde el archivo JSON si existe.
        """
        if not self._file_path.exists():
            return

        try:
            self._last_mtime = self._file_path.stat().st_mtime
            with open(self._file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return

        if not isinstance(data, dict):
            return

        self._profiles.clear()
        self._default_profiles.clear()

        # Cargar perfiles
        profiles_list = data.get("profiles", [])
        if isinstance(profiles_list, list):
            for item in profiles_list:
                try:
                    profile = self._deserialize_profile(item)
                    self._profiles[profile.id] = profile
                except (KeyError, ValueError, TypeError):
                    continue

        # Cargar defaults
        defaults_map = data.get("default_profiles", {})
        if isinstance(defaults_map, dict):
            for app_id, prof_id in defaults_map.items():
                if isinstance(app_id, str) and isinstance(prof_id, str):
                    self._default_profiles[app_id.casefold()] = prof_id

    def _flush(self) -> None:
        """
        Escribe de forma atómica el estado actual al archivo JSON.
        """
        data = {
            "version": 1,
            "default_profiles": self._default_profiles,
            "profiles": [
                self._serialize_profile(p) for p in self._profiles.values()
            ],
        }

        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_file = self._file_path.with_suffix(f".tmp.{os.getpid()}")

        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        tmp_file.replace(self._file_path)
        try:
            self._last_mtime = self._file_path.stat().st_mtime
        except OSError:
            pass

    @staticmethod
    def _serialize_profile(profile: Profile) -> dict:
        return {
            "id": profile.id,
            "name": profile.name,
            "application_id": profile.application_id,
            "dpi": {
                "active": profile.dpi.dpi,
                "shift": profile.dpi.shift_dpi,
            },
            "led_color": profile.led_color,
            "created_at": profile.created_at,
            "updated_at": profile.updated_at,
            "assignments": [
                {
                    "button": {
                        "button_id": assignment.button.button_id,
                        "name": assignment.button.name,
                    },
                    "action": {
                        "action_id": assignment.action.action_id,
                        "name": assignment.action.name,
                        "application_id": assignment.action.application_id,
                        "description": assignment.action.description,
                        "binding_type": assignment.action.binding_type,
                        "binding_value": assignment.action.binding_value,
                    },
                }
                for assignment in profile.list_assignments()
            ],
        }

    @staticmethod
    def _deserialize_profile(item: dict) -> Profile:
        dpi_raw = item["dpi"]
        if isinstance(dpi_raw, int):
            dpi_config = DpiConfiguration(dpi=dpi_raw)
        elif isinstance(dpi_raw, dict):
            dpi_config = DpiConfiguration(
                dpi=dpi_raw.get("active", 800),
                shift_dpi=dpi_raw.get("shift"),
            )
        else:
            dpi_config = DpiConfiguration(800)

        profile = Profile(
            name=item["name"],
            application_id=item["application_id"],
            dpi=dpi_config,
            led_color=item.get("led_color"),
            profile_id=item["id"],
            created_at=item.get("created_at"),
            updated_at=item.get("updated_at"),
        )

        for assign_data in item.get("assignments", []):
            btn_data = assign_data["button"]
            act_data = assign_data["action"]

            button = Button(
                button_id=btn_data["button_id"],
                name=btn_data["name"],
            )
            action = Action(
                action_id=act_data["action_id"],
                name=act_data["name"],
                application_id=act_data["application_id"],
                description=act_data.get("description", ""),
                binding_type=act_data.get("binding_type", "key"),
                binding_value=act_data.get("binding_value", ""),
            )
            profile.assign(button, action)

        return profile
