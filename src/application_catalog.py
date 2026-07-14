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


@dataclass(frozen=True)
class ConfigurableApplication:
    catalog_entry: ApplicationCatalogEntry
    configured: bool
    profile: int | None
    priority: int | None


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


def relate_catalog_to_config(catalog_entries, configured_applications):
    """
    Relaciona entradas del catálogo con aplicaciones configuradas.

    La identidad estable source + application_id determina la asociación.
    """

    configured_by_identity = {}

    for application in configured_applications:
        key = (
            application["source"].casefold(),
            application["application_id"].casefold(),
        )

        configured_by_identity[key] = application

    configurable_applications = []

    for catalog_entry in catalog_entries:
        if not isinstance(catalog_entry, ApplicationCatalogEntry):
            raise TypeError(
                "catalog_entries debe contener instancias "
                "de ApplicationCatalogEntry."
            )

        key = (
            catalog_entry.source.casefold(),
            catalog_entry.application_id.casefold(),
        )

        configured_application = configured_by_identity.get(key)

        configurable_applications.append(
            ConfigurableApplication(
                catalog_entry=catalog_entry,
                configured=configured_application is not None,
                profile=(
                    configured_application["profile"]
                    if configured_application is not None
                    else None
                ),
                priority=(
                    configured_application["priority"]
                    if configured_application is not None
                    else None
                ),
            )
        )

    return configurable_applications
