"""
Servicio de catálogo y plugins de acciones para aplicaciones y juegos.

Inspirado en el sistema de asignaciones de Logitech G-HUB:
- Organiza las acciones por categorías (Habilidades, Combate, Movimiento, Interfaz, Macros).
- Carga manifiestos de presets modulares desde presets/ y ~/.config/g502-profile-manager/presets/.
- Soporta el registro de acciones personalizadas por aplicación.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

from domain import Action, Application


DEFAULT_BUILTIN_DIR = Path(__file__).resolve().parent.parent.parent / "presets"
DEFAULT_USER_DIR = Path.home() / ".config" / "g502-profile-manager" / "presets"


class ActionCatalogService:
    """
    Gestiona el descubrimiento, categorización y carga de bibliotecas de acciones
    para videojuegos y aplicaciones de software.
    """

    def __init__(self, search_paths: Sequence[Path] | None = None):
        if search_paths is None:
            self._search_paths = [DEFAULT_BUILTIN_DIR, DEFAULT_USER_DIR]
        else:
            self._search_paths = [Path(p) for p in search_paths]

        # Estructura: app_id (casefold) -> {"name": str, "description": str, "actions": list[Action]}
        self._catalogs: dict[str, dict] = {}
        self.reload()

    def reload(self) -> None:
        """
        Escanea las rutas configuradas y carga todos los manifiestos JSON de presets.
        Los manifiestos encontrados en rutas posteriores sobreescriben o complementan
        los anteriores (permitiendo al usuario personalizar presets integrados).
        """
        self._catalogs.clear()

        for directory in self._search_paths:
            if not directory.is_dir():
                continue

            for file_path in sorted(directory.glob("*.json")):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    self._parse_and_register_manifest(data)
                except (json.JSONDecodeError, OSError, ValueError):
                    continue

    def _parse_and_register_manifest(self, data: dict) -> None:
        """Parsea un diccionario de manifiesto y registra sus acciones."""
        if not isinstance(data, dict):
            return

        app_id = data.get("application_id")
        if not isinstance(app_id, str) or not app_id.strip():
            return

        app_key = app_id.strip().casefold()
        app_name = str(data.get("name", app_id)).strip()
        description = str(data.get("description", "")).strip()

        if app_key not in self._catalogs:
            self._catalogs[app_key] = {
                "application_id": app_id.strip(),
                "name": app_name,
                "description": description,
                "actions": {},
            }
        else:
            if app_name and app_name != app_id:
                self._catalogs[app_key]["name"] = app_name

        raw_actions = data.get("actions", [])
        if isinstance(raw_actions, list):
            for item in raw_actions:
                if not isinstance(item, dict):
                    continue
                action_id = item.get("action_id")
                name = item.get("name")
                if not action_id or not name:
                    continue

                action = Action(
                    action_id=str(action_id).strip(),
                    name=str(name).strip(),
                    application_id=app_id.strip(),
                    description=str(item.get("description", "")).strip(),
                    binding_type=str(item.get("binding_type", "key")).strip(),
                    binding_value=str(item.get("binding_value", "")).strip(),
                    category=str(item.get("category", "General")).strip(),
                )
                self._catalogs[app_key]["actions"][action.action_id] = action

    def has_catalog(self, application_id: str) -> bool:
        """Determina si existe un catálogo cargado para el identificador dado."""
        if not isinstance(application_id, str):
            return False
        return application_id.strip().casefold() in self._catalogs

    def get_application_name(self, application_id: str) -> str | None:
        """Obtiene el nombre representativo del juego o aplicación en el catálogo."""
        if not isinstance(application_id, str):
            return None
        catalog = self._catalogs.get(application_id.strip().casefold())
        return catalog["name"] if catalog else None

    def get_actions_for_application(self, application_id: str) -> tuple[Action, ...]:
        """
        Retorna la lista completa de acciones disponibles para una aplicación.
        """
        if not isinstance(application_id, str):
            return ()
        catalog = self._catalogs.get(application_id.strip().casefold())
        if not catalog:
            return ()
        return tuple(catalog["actions"].values())

    def get_categories_for_application(
        self, application_id: str
    ) -> dict[str, list[Action]]:
        """
        Retorna las acciones agrupadas por sus categorías (estilo Logitech G-HUB).
        Ejemplo: {'Habilidades': [Action(...), ...], 'Combate': [...]}
        """
        actions = self.get_actions_for_application(application_id)
        categories: dict[str, list[Action]] = {}

        for action in actions:
            cat = action.category or "General"
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(action)

        return categories

    def register_custom_action(
        self,
        application_id: str,
        action: Action,
        persist_user_preset: bool = False,
    ) -> bool:
        """
        Registra una acción personalizada en el catálogo en tiempo de ejecución.
        Opcionalmente la persiste en el directorio de usuario ~/.config/g502-profile-manager/presets/.
        """
        if not isinstance(application_id, str) or not application_id.strip():
            return False
        if not isinstance(action, Action):
            return False

        app_key = application_id.strip().casefold()
        if app_key not in self._catalogs:
            self._catalogs[app_key] = {
                "application_id": application_id.strip(),
                "name": application_id.strip(),
                "description": "Perfil de aplicación con acciones personalizadas",
                "actions": {},
            }

        self._catalogs[app_key]["actions"][action.action_id] = action

        if persist_user_preset:
            self._save_user_custom_preset(application_id)

        return True

    def _save_user_custom_preset(self, application_id: str) -> None:
        """Persiste el catálogo de una aplicación en el directorio de usuario."""
        app_key = application_id.strip().casefold()
        catalog = self._catalogs.get(app_key)
        if not catalog:
            return

        DEFAULT_USER_DIR.mkdir(parents=True, exist_ok=True)
        safe_id = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in app_key)
        file_path = DEFAULT_USER_DIR / f"{safe_id}.json"

        data = {
            "application_id": catalog["application_id"],
            "name": catalog["name"],
            "description": catalog["description"],
            "actions": [
                {
                    "action_id": a.action_id,
                    "name": a.name,
                    "category": a.category,
                    "description": a.description,
                    "binding_type": a.binding_type,
                    "binding_value": a.binding_value,
                }
                for a in catalog["actions"].values()
            ],
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def populate_application_actions(self, application: Application) -> int:
        """
        Rellena una instancia de dominio Application con todas las acciones
        disponibles en el catálogo para su application_id.
        Retorna el número de nuevas acciones añadidas.
        """
        if not isinstance(application, Application):
            raise TypeError("application debe ser una instancia de Application.")

        actions = self.get_actions_for_application(application.application_id)
        added = 0
        for action in actions:
            if not application.has_action(action.action_id):
                application.add_action(action)
                added += 1

        return added

    def list_supported_applications(self) -> list[dict[str, str | int]]:
        """
        Lista todas las aplicaciones con catálogo disponible en el sistema.
        """
        result = []
        for cat in self._catalogs.values():
            result.append(
                {
                    "application_id": cat["application_id"],
                    "name": cat["name"],
                    "description": cat["description"],
                    "action_count": len(cat["actions"]),
                }
            )
        return result
