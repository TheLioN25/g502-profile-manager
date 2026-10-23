"""
Módulo de almacenamiento y persistencia para perfiles.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import logging
import os
from pathlib import Path
import shutil
import tempfile
import threading
import time
from typing import Protocol

logger = logging.getLogger("g502.storage")


class CorruptedProfileRepositoryError(RuntimeError):
    """Excepción lanzada cuando el archivo de perfiles está corrupto y no puede sobrescribirse."""
    pass

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

    def export_data(self, application_id: str | None = None) -> dict:
        """Exporta perfiles y predeterminados a un diccionario serializable."""
        ...

    def import_data(self, data: dict, overwrite: bool = False) -> tuple[int, int]:
        """Importa perfiles desde un diccionario o respaldo JSON."""
        ...


# Fuente canónica de persistencia de perfiles en disco.
# Cualquier modificación en esta ruta debe sincronizarse en docs/ARCHITECTURE.md y READMEs.
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
        self._lock = threading.RLock()
        self._is_corrupted: bool = False
        self._corrupt_backup_path: Path | None = None
        self._load()

    @property
    def is_corrupted(self) -> bool:
        """Indica si el archivo de perfiles en disco está corrupto."""
        with self._lock:
            return self._is_corrupted

    @property
    def corrupt_backup_path(self) -> Path | None:
        """Ruta al archivo de respaldo del JSON corrupto si existió."""
        with self._lock:
            return self._corrupt_backup_path

    @contextmanager
    def _file_lock(self):
        """Bloqueo exclusivo a nivel de archivo para coordinar CLI y GUI (inter-proceso)."""
        lock_path = self._file_path.with_name(f"{self._file_path.name}.lock")
        try:
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            with open(lock_path, "a") as fd:
                try:
                    fcntl.flock(fd.fileno(), fcntl.LOCK_EX)
                except OSError:
                    pass
                try:
                    yield
                finally:
                    try:
                        fcntl.flock(fd.fileno(), fcntl.LOCK_UN)
                    except OSError:
                        pass
        except OSError:
            yield

    @property
    def file_path(self) -> Path:
        """Ruta al archivo JSON de persistencia."""
        return self._file_path

    def _handle_corrupted_file(self, err: Exception) -> None:
        ts = int(time.time())
        backup_path = self._file_path.with_name(f"{self._file_path.name}.corrupt-{ts}")
        try:
            shutil.copy2(self._file_path, backup_path)
        except OSError as copy_err:
            logger.warning(f"No se pudo respaldar el archivo corrupto: {copy_err}")

        self._is_corrupted = True
        self._corrupt_backup_path = backup_path
        logger.error(
            f"El archivo de perfiles '{self._file_path}' está corrupto ({err}). "
            f"Se creó una copia de seguridad en '{backup_path}'. "
            "Las operaciones de guardado quedan bloqueadas para evitar pérdida de datos."
        )

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

        with self._lock:
            with self._file_lock():
                self._reload_if_needed()
                self._profiles[profile.id] = profile
                self._flush()

    def get_by_id(self, profile_id: str) -> Profile | None:
        """
        Obtiene un perfil por su ID.
        """
        if not isinstance(profile_id, str):
            return None
        with self._lock:
            self._reload_if_needed()
            return self._profiles.get(profile_id.strip())

    def get_by_application(self, application_id: str) -> tuple[Profile, ...]:
        """
        Devuelve todos los perfiles asociados a la aplicación dada.
        """
        if not isinstance(application_id, str):
            return ()

        with self._lock:
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
        with self._lock:
            self._reload_if_needed()
            return tuple(self._profiles.values())

    def get_default_profile_id(self, application_id: str) -> str | None:
        """
        Devuelve el ID del perfil predeterminado para una aplicación.
        """
        if not isinstance(application_id, str):
            return None
        with self._lock:
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

        with self._lock:
            with self._file_lock():
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

        with self._lock:
            with self._file_lock():
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

    def export_data(self, application_id: str | None = None) -> dict:
        """
        Exporta los perfiles y mapeos predeterminados a un diccionario serializable.
        Si se especifica application_id, filtra únicamente dicha aplicación.
        """
        with self._lock:
            self._reload_if_needed()
            if application_id is not None:
                clean_app_id = application_id.strip().casefold()
                profiles = [
                    self._serialize_profile(p)
                    for p in self._profiles.values()
                    if p.application_id.casefold() == clean_app_id
                ]
                defaults = {
                    app_id: prof_id
                    for app_id, prof_id in self._default_profiles.items()
                    if app_id.casefold() == clean_app_id
                }
            else:
                profiles = [self._serialize_profile(p) for p in self._profiles.values()]
                defaults = dict(self._default_profiles)

            return {
                "version": 1,
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "default_profiles": defaults,
                "profiles": profiles,
            }

    def import_data(self, data: dict | list, overwrite: bool = False) -> tuple[int, int]:
        """
        Importa perfiles desde una estructura de datos exportada.
        """
        if isinstance(data, list):
            profiles_raw = data
            defaults_map = {}
        elif isinstance(data, dict):
            profiles_raw = data.get("profiles", [])
            defaults_map = data.get("default_profiles", {})
        else:
            raise ValueError("Los datos a importar deben ser un diccionario o lista JSON válida.")

        if not isinstance(profiles_raw, list):
            raise ValueError("El formato de importación es inválido: 'profiles' debe ser una lista.")

        with self._lock:
            with self._file_lock():
                self._reload_if_needed()
                imported = 0
                skipped = 0

                for item in profiles_raw:
                    if not isinstance(item, dict):
                        skipped += 1
                        continue
                    try:
                        profile = self._deserialize_profile(item)
                    except Exception:
                        skipped += 1
                        continue

                    if profile.id in self._profiles and not overwrite:
                        skipped += 1
                        continue

                    self._profiles[profile.id] = profile
                    imported += 1

                if isinstance(defaults_map, dict):
                    for app_id, prof_id in defaults_map.items():
                        if isinstance(app_id, str) and isinstance(prof_id, str):
                            clean_app = app_id.strip().casefold()
                            clean_prof = prof_id.strip()
                            if clean_prof in self._profiles:
                                if overwrite or clean_app not in self._default_profiles:
                                    self._default_profiles[clean_app] = clean_prof

                if imported > 0:
                    self._flush()

                return (imported, skipped)

    def _load(self) -> None:
        """
        Carga los datos desde el archivo JSON si existe.
        Preserva y respalda el archivo original ante corrupción o errores de sintaxis.
        """
        if not self._file_path.exists():
            return

        try:
            if self._file_path.stat().st_size == 0:
                return
        except OSError:
            return

        try:
            self._last_mtime = self._file_path.stat().st_mtime
            with open(self._file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as err:
            self._handle_corrupted_file(err)
            return

        if not isinstance(data, dict):
            self._handle_corrupted_file(ValueError("El archivo JSON debe contener un objeto dict raíz."))
            return

        self._is_corrupted = False
        self._corrupt_backup_path = None
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
        Lanza CorruptedProfileRepositoryError si el archivo original estaba corrupto.
        """
        if self._is_corrupted:
            raise CorruptedProfileRepositoryError(
                f"Operación abortada: el archivo '{self._file_path}' está corrupto. "
                f"Se preservó el archivo original en '{self._corrupt_backup_path}'."
            )

        data = {
            "version": 1,
            "default_profiles": self._default_profiles,
            "profiles": [
                self._serialize_profile(p) for p in self._profiles.values()
            ],
        }

        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=self._file_path.parent,
            prefix=f"{self._file_path.name}.tmp.",
            delete=False,
        ) as tmp:
            json.dump(data, tmp, indent=4, ensure_ascii=False)
            tmp_path = Path(tmp.name)

        tmp_path.replace(self._file_path)
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
            "led_mode": profile.led_mode,
            "led_duration": profile.led_duration,
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
            led_mode=item.get("led_mode", "on"),
            led_duration=item.get("led_duration"),
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
