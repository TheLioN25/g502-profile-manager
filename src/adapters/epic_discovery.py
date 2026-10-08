"""
Módulo de descubrimiento de juegos y aplicaciones de Epic Games en Linux.

Soporta múltiples lanzadores y métodos de instalación de Epic Games en Linux:
1. Heroic Games Launcher (Legendary): ~/.config/heroic/legendaryConfig/legendary/installed.json
   y versión Flatpak: ~/.var/app/com.heroicgameslauncher.hgl/config/heroic/...
2. Legendary CLI: ~/.config/legendary/installed.json
3. Lutris: ~/.local/share/lutris/pga.db (juegos con service='epic')
4. Epic Games Store (Wine/Proton): drive_c/ProgramData/Epic/EpicGamesLauncher/Data/Manifests/*.item
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from typing import Iterable, Sequence

from .application_resolver import ActiveApplication
from .process_discovery import ProcessInfo


DEFAULT_HEROIC_INSTALLED_FILES = (
    Path.home() / ".config/heroic/legendaryConfig/legendary/installed.json",
    Path.home() / ".var/app/com.heroicgameslauncher.hgl/config/heroic/legendaryConfig/legendary/installed.json",
    Path.home() / ".config/legendary/installed.json",
)

DEFAULT_LUTRIS_DB = Path.home() / ".local/share/lutris/pga.db"


@dataclass(frozen=True)
class EpicAppManifest:
    """Representa los metadatos de un juego de Epic Games instalado en el sistema."""
    app_name: str
    title: str
    install_path: str = ""
    executable: str = ""

    @property
    def app_id(self) -> str:
        """Identificador unificado con prefijo 'epic:'."""
        return f"epic:{self.app_name.strip()}"


def discover_heroic_installed_apps(
    installed_files: Sequence[Path] = DEFAULT_HEROIC_INSTALLED_FILES,
) -> list[EpicAppManifest]:
    """
    Lee archivos installed.json generados por Heroic Games Launcher o Legendary.
    """
    discovered: dict[str, EpicAppManifest] = {}

    for file_path in installed_files:
        path = Path(file_path).expanduser().resolve()
        if not path.is_file():
            continue

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, dict):
                for app_key, details in data.items():
                    if not isinstance(details, dict):
                        continue

                    name = details.get("app_name") or app_key
                    title = details.get("title") or name
                    install_path = details.get("install_path", "")
                    executable = details.get("executable", "")

                    if name not in discovered:
                        discovered[name] = EpicAppManifest(
                            app_name=str(name).strip(),
                            title=str(title).strip(),
                            install_path=str(install_path).strip(),
                            executable=str(executable).strip(),
                        )
        except (json.JSONDecodeError, OSError):
            continue

    return list(discovered.values())


def discover_lutris_epic_apps(
    db_path: Path = DEFAULT_LUTRIS_DB,
) -> list[EpicAppManifest]:
    """
    Consulta la base de datos local de Lutris en busca de juegos vinculados a Epic Games.
    """
    path = Path(db_path).expanduser().resolve()
    if not path.is_file():
        return []

    discovered = []
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT slug, name, directory FROM games WHERE service = 'epic' OR installer_slug LIKE '%epic%'"
        )
        for slug, name, directory in cursor.fetchall():
            if slug:
                discovered.append(
                    EpicAppManifest(
                        app_name=str(slug).strip(),
                        title=str(name or slug).strip(),
                        install_path=str(directory or "").strip(),
                    )
                )
        conn.close()
    except (sqlite3.Error, OSError):
        pass

    return discovered


def discover_all_installed_epic_apps() -> list[EpicAppManifest]:
    """
    Descubre todos los juegos de Epic Games instalados en el sistema mediante
    todas las fuentes disponibles (Heroic, Legendary, Lutris).
    """
    apps_by_name: dict[str, EpicAppManifest] = {}

    for app in discover_heroic_installed_apps():
        apps_by_name[app.app_name.casefold()] = app

    for app in discover_lutris_epic_apps():
        if app.app_name.casefold() not in apps_by_name:
            apps_by_name[app.app_name.casefold()] = app

    return sorted(apps_by_name.values(), key=lambda a: a.title.casefold())


def discover_active_epic_apps(
    processes: Iterable[ProcessInfo],
    installed_apps: Iterable[EpicAppManifest] | None = None,
) -> list[EpicAppManifest]:
    """
    Identifica si algún juego de Epic Games instalado se encuentra actualmente en ejecución.
    Supervisa la línea de comandos (ej. 'legendary launch <app_name>') y las rutas de ejecutables.
    """
    if installed_apps is None:
        installed_apps = discover_all_installed_epic_apps()

    apps_list = list(installed_apps)
    if not apps_list:
        return []

    active_apps: dict[str, EpicAppManifest] = {}

    for proc in processes:
        cmdline = proc.command or ""
        exe = proc.executable_path or ""
        full_text = f"{exe} {cmdline}".casefold()

        for app in apps_list:
            app_name_lower = app.app_name.casefold()
            # 1. Coincidencia por invocador de Legendary / Heroic
            if f"launch {app_name_lower}" in full_text or f"--app {app_name_lower}" in full_text:
                active_apps[app.app_id] = app
                continue

            # 2. Coincidencia por ruta de instalación
            if app.install_path and app.install_path.casefold() in full_text:
                active_apps[app.app_id] = app
                continue

            # 3. Coincidencia por ejecutable específico
            if app.executable and Path(app.executable).name.casefold() in full_text:
                active_apps[app.app_id] = app
                continue

    return list(active_apps.values())


def resolve_epic_applications(
    active_epic_apps: Iterable[EpicAppManifest],
) -> list[ActiveApplication]:
    """
    Convierte los manifiestos activos de Epic Games en identidades ActiveApplication.
    """
    results = []
    for app in active_epic_apps:
        results.append(
            ActiveApplication(
                name=app.title,
                application_id=app.app_id,
                source="epic",
                executable=app.executable or app.install_path or app.app_name,
                desktop_files=(),
                process_ids=(),
                ambiguous=False,
            )
        )
    return results
