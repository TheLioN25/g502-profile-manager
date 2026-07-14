"""
Gestión de aplicaciones configurables para G502 Profile Manager.

Este módulo coordina el descubrimiento de aplicaciones instaladas,
la construcción del catálogo y su relación con la configuración persistente.
"""

from pathlib import Path

from application_catalog import (
    build_steam_catalog,
    relate_catalog_to_config,
)
from config_manager import list_applications
from steam_discovery import discover_installed_steam_apps


DEFAULT_STEAM_LIBRARYFOLDERS_FILE = (
    Path.home()
    / ".local/share/Steam/steamapps/libraryfolders.vdf"
)


def list_configurable_applications(
    libraryfolders_file=DEFAULT_STEAM_LIBRARYFOLDERS_FILE,
):
    """
    Devuelve las aplicaciones instaladas disponibles para configuración.

    Construye el catálogo de Steam y lo relaciona con las asociaciones
    persistentes existentes.
    """

    steam_applications = discover_installed_steam_apps(
        libraryfolders_file,
    )

    catalog_entries = build_steam_catalog(
        steam_applications,
    )

    configured_applications = list_applications()

    return relate_catalog_to_config(
        catalog_entries,
        configured_applications,
    )
