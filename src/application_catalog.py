"""
Catálogo de aplicaciones configurables para G502 Profile Manager.

Este módulo transforma aplicaciones instaladas procedentes de distintas
fuentes en elementos que podrán ser mostrados y seleccionados por el usuario.
"""

from dataclasses import dataclass

from steam_discovery import SteamAppManifest


@dataclass(frozen=True)
class ApplicationCatalogEntry:
    name: str
    application_id: str
    source: str


def build_steam_catalog(steam_applications):
    """
    Convierte aplicaciones instaladas de Steam en entradas del catálogo.
    """

    catalog_entries = []

    for steam_application in steam_applications:
        if not isinstance(steam_application, SteamAppManifest):
            raise TypeError(
                "steam_applications debe contener instancias "
                "de SteamAppManifest."
            )

        catalog_entries.append(
            ApplicationCatalogEntry(
                name=steam_application.name,
                application_id=f"steam:{steam_application.app_id}",
                source="steam",
            )
        )

    return sorted(
        catalog_entries,
        key=lambda application: (
            application.name.casefold(),
            application.application_id.casefold(),
        ),
    )
