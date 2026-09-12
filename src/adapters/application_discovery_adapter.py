"""
Adaptador para el descubrimiento unificado de aplicaciones (Steam y entradas .desktop).
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable

from desktop_entries import (
    DESKTOP_DIRECTORIES,
    DesktopEntry,
    discover_desktop_entries,
    parse_desktop_entry,
)
from domain import Application
from epic_discovery import (
    EpicAppManifest,
    discover_all_installed_epic_apps,
)
from steam_discovery import (
    SteamAppManifest,
    discover_installed_steam_apps,
)

DEFAULT_STEAM_LIBRARYFOLDERS_FILE = (
    Path.home() / ".local/share/Steam/steamapps/libraryfolders.vdf"
)


class ApplicationDiscoveryAdapter:
    """
    Coordina el descubrimiento de aplicaciones instaladas procedentes de diversas fuentes
    (Steam, Epic Games y entradas .desktop) y las transforma en entidades de dominio 'Application'.
    """

    def __init__(
        self,
        steam_libraryfolders_file: Path | str = DEFAULT_STEAM_LIBRARYFOLDERS_FILE,
        desktop_directories: Iterable[Path | str] = DESKTOP_DIRECTORIES,
    ):
        self._steam_file = Path(steam_libraryfolders_file).expanduser().resolve()
        self._desktop_dirs = [Path(d).expanduser().resolve() for d in desktop_directories]

    def discover_steam_applications(
        self,
        reader: Callable[[Path], list[SteamAppManifest]] = discover_installed_steam_apps,
    ) -> list[Application]:
        """
        Descubre juegos de Steam instalados y los transforma en entidades Application.
        """
        if not self._steam_file.exists():
            return []

        steam_apps = reader(self._steam_file)
        applications: list[Application] = []

        for app in steam_apps:
            app_id = f"steam:{app.app_id}"
            applications.append(
                Application(
                    application_id=app_id,
                    name=app.name,
                )
            )

        return sorted(applications, key=lambda a: a.name.casefold())

    def discover_epic_applications(
        self,
        finder: Callable[[], list[EpicAppManifest]] = discover_all_installed_epic_apps,
    ) -> list[Application]:
        """
        Descubre juegos de Epic Games instalados en Linux (Heroic, Legendary, Lutris)
        y los transforma en entidades Application.
        """
        epic_apps = finder()
        applications: list[Application] = []

        for app in epic_apps:
            applications.append(
                Application(
                    application_id=app.app_id,
                    name=app.title,
                )
            )

        return sorted(applications, key=lambda a: a.name.casefold())

    def discover_desktop_applications(
        self,
        finder: Callable[..., list[Path]] = discover_desktop_entries,
        parser: Callable[[Path], DesktopEntry | None] = parse_desktop_entry,
    ) -> list[Application]:
        """
        Descubre aplicaciones de escritorio estándar mediante archivos .desktop
        y las transforma en entidades Application del dominio.
        """
        desktop_files = finder(self._desktop_dirs)
        apps_by_id: dict[str, Application] = {}

        for file_path in desktop_files:
            entry = parser(file_path)
            if entry is None or not entry.executable:
                continue

            app_id = f"desktop:{entry.executable.casefold()}"
            if app_id not in apps_by_id:
                apps_by_id[app_id] = Application(
                    application_id=app_id,
                    name=entry.name,
                )

        return sorted(apps_by_id.values(), key=lambda a: a.name.casefold())

    def discover_all_applications(self) -> tuple[Application, ...]:
        """
        Devuelve el conjunto completo de aplicaciones descubiertas (Steam + Epic Games + Desktop),
        desduplicadas por application_id.
        """
        steam_apps = self.discover_steam_applications()
        epic_apps = self.discover_epic_applications()
        desktop_apps = self.discover_desktop_applications()

        combined: dict[str, Application] = {}

        # 1. Priorizar Steam para juegos de Steam
        for app in steam_apps:
            combined[app.application_id] = app

        # 2. Priorizar Epic Games
        for app in epic_apps:
            if app.application_id not in combined:
                combined[app.application_id] = app

        # 3. Aplicaciones de escritorio
        for app in desktop_apps:
            if app.application_id not in combined:
                combined[app.application_id] = app

        return tuple(sorted(combined.values(), key=lambda a: a.name.casefold()))

    def get_application_by_id(self, application_id: str) -> Application | None:
        """
        Busca una aplicación instalada por su identificador estable.
        """
        if not isinstance(application_id, str) or not application_id.strip():
            return None

        target_id = application_id.strip().casefold()
        for app in self.discover_all_applications():
            if app.application_id.casefold() == target_id:
                return app

        return None
