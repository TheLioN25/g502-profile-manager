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

IGNORED_GAME_PATTERNS = (
    "proton",
    "steam linux runtime",
    "steamworks common",
    "steam controller",
    "soundtrack",
    "dedicated server",
)


def generate_default_game_actions(app_id: str, game_name: str) -> list[Action]:
    """
    Genera automáticamente un catálogo estándar de acciones categorizadas para juegos
    (Combate, Movimiento, Habilidades, Interacción) cuando se descarga un juego nuevo
    de Steam o Epic Games.
    """
    safe_prefix = "".join(c if c.isalnum() else "_" for c in game_name.lower())[:8].strip("_") or "game"
    return [
        # Combate
        Action(f"{safe_prefix}_fire", "Disparo Principal", app_id, "Acción de ataque o disparo primario", "special", "button 1", "Combate"),
        Action(f"{safe_prefix}_aim", "Apuntar / Secundario", app_id, "Apuntar con mira o ataque alternativo", "special", "button 2", "Combate"),
        Action(f"{safe_prefix}_melee", "Ataque Cuerpo a Cuerpo", app_id, "Golpe cuerpo a cuerpo rápido", "key", "e", "Combate"),
        Action(f"{safe_prefix}_reload", "Recargar", app_id, "Recargar munición", "key", "r", "Combate"),
        Action(f"{safe_prefix}_weapon_switch", "Cambiar Arma", app_id, "Alternar armamento", "key", "q", "Combate"),

        # Habilidades
        Action(f"{safe_prefix}_skill_1", "Habilidad 1", app_id, "Primera habilidad", "key", "1", "Habilidades"),
        Action(f"{safe_prefix}_skill_2", "Habilidad 2", app_id, "Segunda habilidad", "key", "2", "Habilidades"),
        Action(f"{safe_prefix}_skill_3", "Habilidad 3", app_id, "Tercera habilidad", "key", "3", "Habilidades"),
        Action(f"{safe_prefix}_ultimate", "Habilidad Definitiva (Ult)", app_id, "Habilidad de élite o definitiva", "key", "4", "Habilidades"),

        # Movimiento
        Action(f"{safe_prefix}_jump", "Saltar", app_id, "Saltar obstáculo", "key", "space", "Movimiento"),
        Action(f"{safe_prefix}_crouch", "Agacharse / Deslizarse", app_id, "Agacharse o deslizarse", "key", "leftctrl", "Movimiento"),
        Action(f"{safe_prefix}_sprint", "Correr", app_id, "Correr a gran velocidad", "key", "leftshift", "Movimiento"),
        Action(f"{safe_prefix}_dodge", "Esquivar", app_id, "Rodar o esquivar", "key", "c", "Movimiento"),

        # Interacción
        Action(f"{safe_prefix}_interact", "Usar / Interactuar", app_id, "Abrir, saquear o interactuar", "key", "f", "Interacción"),
        Action(f"{safe_prefix}_map", "Mapa", app_id, "Abrir mapa de navegación", "key", "m", "Interacción"),
        Action(f"{safe_prefix}_inventory", "Inventario", app_id, "Abrir mochila o inventario", "key", "tab", "Interacción"),
        Action(f"{safe_prefix}_voice", "Chat de Voz (VoIP)", app_id, "Hablar con el equipo", "key", "v", "Interacción"),
    ]


class ActionCatalogService:
    """
    Gestiona el descubrimiento, categorización y carga de bibliotecas de acciones
    para videojuegos y aplicaciones de software (Steam, Epic Games y escritorio).
    """

    def __init__(self, search_paths: Sequence[Path] | None = None):
        if search_paths is None:
            self._search_paths = [DEFAULT_BUILTIN_DIR, DEFAULT_USER_DIR]
        else:
            self._search_paths = [Path(p) for p in search_paths]

        # Estructura: app_id (casefold) -> {"name": str, "description": str, "actions": dict[str, Action]}
        self._catalogs: dict[str, dict] = {}
        self._alias_map: dict[str, str] = {}
        self.reload()

    def reload(self) -> None:
        """
        Escanea las rutas configuradas y carga todos los manifiestos JSON de presets.
        Los manifiestos encontrados en rutas posteriores sobreescriben o complementan
        los anteriores (permitiendo al usuario personalizar presets integrados).
        """
        self._catalogs.clear()
        self._alias_map.clear()

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

        self._alias_map[app_key] = app_key
        if app_name:
            self._alias_map[app_name.casefold()] = app_key

        raw_aliases = data.get("aliases", [])
        if isinstance(raw_aliases, (list, tuple)):
            for alias in raw_aliases:
                if isinstance(alias, str) and alias.strip():
                    self._alias_map[alias.strip().casefold()] = app_key

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

    def _resolve_app_key(self, application_id: str) -> str | None:
        """
        Resuelve un identificador de aplicación o alias hacia la clave canónica del catálogo.
        Soporta coincidencias exactas, prefijos (steam:, desktop:, etc.), alias registrados
        y búsqueda por similitud normalizada para variantes de nombres o lanzadores.
        """
        if not isinstance(application_id, str):
            return None
        raw = application_id.strip().casefold()
        if not raw:
            return None

        if raw in self._catalogs:
            return raw
        if raw in self._alias_map:
            return self._alias_map[raw]

        if ":" in raw:
            bare = raw.split(":", 1)[1].strip()
            if bare in self._catalogs:
                return bare
            if bare in self._alias_map:
                return self._alias_map[bare]

        norm_query = "".join(c for c in raw if c.isalnum())
        if norm_query:
            for alias, target_key in self._alias_map.items():
                norm_alias = "".join(c for c in alias if c.isalnum())
                if norm_query == norm_alias:
                    return target_key
            if len(norm_query) >= 4:
                for alias, target_key in self._alias_map.items():
                    norm_alias = "".join(c for c in alias if c.isalnum())
                    if len(norm_alias) >= 4 and (norm_query.startswith(norm_alias) or norm_alias in norm_query):
                        return target_key

        return None

    def has_catalog(self, application_id: str) -> bool:
        """Determina si existe un catálogo cargado para el identificador dado o sus alias."""
        return self._resolve_app_key(application_id) is not None

    def get_application_name(self, application_id: str) -> str | None:
        """Obtiene el nombre representativo del juego o aplicación en el catálogo."""
        resolved = self._resolve_app_key(application_id)
        if not resolved:
            return None
        catalog = self._catalogs.get(resolved)
        return catalog["name"] if catalog else None

    def get_actions_for_application(self, application_id: str) -> tuple[Action, ...]:
        """
        Retorna la lista completa de acciones disponibles para una aplicación.
        """
        resolved = self._resolve_app_key(application_id)
        if not resolved:
            return ()
        catalog = self._catalogs.get(resolved)
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

    def sync_with_installed_applications(
        self,
        installed_apps: Iterable[Application],
        auto_generate_for_games: bool = True,
        persist: bool = True,
    ) -> list[str]:
        """
        Sincroniza el catálogo con los juegos/apps instalados en el sistema (Steam y Epic Games).
        Si se detecta un juego recién descargado que aún no tiene catálogo,
        genera dinámicamente sus acciones en el acto para que estén disponibles inmediatamente.
        Retorna los application_ids de los catálogos nuevos generados.
        """
        newly_added = []
        for app in installed_apps:
            resolved = self._resolve_app_key(app.application_id) or self._resolve_app_key(app.name)
            if resolved:
                app_key = app.application_id.strip().casefold()
                self._alias_map[app_key] = resolved
                continue

            app_key = app.application_id.strip().casefold()
            is_game = app.application_id.startswith("steam:") or app.application_id.startswith("epic:")
            if is_game and auto_generate_for_games:
                    name_lower = app.name.strip().casefold()
                    if any(ignored in name_lower for ignored in IGNORED_GAME_PATTERNS):
                        continue

                    actions = generate_default_game_actions(app.application_id, app.name)
                    self._catalogs[app_key] = {
                        "application_id": app.application_id,
                        "name": app.name,
                        "description": f"Catálogo dinámico generado para {app.name}",
                        "actions": {a.action_id: a for a in actions},
                    }
                    if persist:
                        self._save_user_custom_preset(app.application_id)
                    newly_added.append(app.application_id)

        return newly_added

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

    def list_supported_applications(
        self,
        installed_app_ids: set[str] | None = None,
    ) -> list[dict[str, str | int]]:
        """
        Lista las aplicaciones con catálogo disponible.
        Si se especifica installed_app_ids, filtra para mostrar ÚNICAMENTE
        las aplicaciones que efectivamente están instaladas en el sistema.
        """
        result = []
        installed_resolved: set[str] | None = None
        if installed_app_ids is not None:
            installed_resolved = {
                self._resolve_app_key(i) or i.casefold() for i in installed_app_ids
            }

        for cat in self._catalogs.values():
            app_id = cat["application_id"]
            if installed_resolved is not None:
                if app_id != "desktop:general" and app_id.casefold() not in installed_resolved:
                    continue

            result.append(
                {
                    "application_id": app_id,
                    "name": cat["name"],
                    "description": cat["description"],
                    "action_count": len(cat["actions"]),
                }
            )
        return result
