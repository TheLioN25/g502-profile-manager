"""
Descubrimiento de aplicaciones ejecutadas mediante Steam.

Este módulo identifica lanzamientos activos de Steam usando la información
expuesta por los procesos supervisores creados durante el lanzamiento.
"""

from dataclasses import dataclass
from pathlib import Path
import re


STEAM_LAUNCH_PATTERN = re.compile(
    r"(?:^|\s)SteamLaunch\s+AppId=(\d+)(?:\s|$)",
    re.IGNORECASE,
)

VDF_KEY_VALUE_PATTERN = re.compile(
    r'^\s*"([^"]+)"\s+"([^"]*)"\s*$'
)

@dataclass(frozen=True)
class SteamLaunch:
    app_id: int
    supervisor_pid: int
    command: str

@dataclass(frozen=True)
class SteamAppManifest:
    app_id: int
    name: str
    install_dir: str
    manifest_file: str
    library_path: str


@dataclass(frozen=True)
class ActiveSteamApplication:
    launch: SteamLaunch
    manifest: SteamAppManifest


def extract_steam_app_id(process):
    """
    Extrae el AppID de un proceso supervisor de lanzamiento de Steam.

    Devuelve None cuando el proceso no representa un lanzamiento reconocible.
    """
    command = getattr(process, "command", "") or ""
    match = STEAM_LAUNCH_PATTERN.search(command)

    if match is None:
        return None

    return int(match.group(1))


def discover_steam_launches(processes):
    """
    Devuelve los lanzamientos activos de Steam detectados en los procesos.

    Evita devolver varias veces el mismo AppID.
    """
    launches_by_app_id = {}

    for process in processes:
        app_id = extract_steam_app_id(process)

        if app_id is None:
            continue

        if app_id not in launches_by_app_id:
            launches_by_app_id[app_id] = SteamLaunch(
                app_id=app_id,
                supervisor_pid=process.pid,
                command=process.command,
            )

    return list(launches_by_app_id.values())

def discover_steam_libraries(libraryfolders_file):
    """
    Descubre las rutas de bibliotecas configuradas por Steam.

    Lee únicamente las claves path pertenecientes directamente a cada
    bloque de biblioteca e ignora los bloques anidados como apps.
    """
    libraryfolders_file = Path(libraryfolders_file)

    try:
        lines = libraryfolders_file.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines()
    except OSError:
        return []

    libraries = []
    depth = 0

    for line in lines:
        stripped = line.strip()

        if stripped == "{":
            depth += 1
            continue

        if stripped == "}":
            depth -= 1
            continue

        if depth != 2:
            continue

        match = VDF_KEY_VALUE_PATTERN.match(line)

        if match is None:
            continue

        key, value = match.groups()

        if key.casefold() != "path":
            continue

        library_path = Path(value)

        if library_path not in libraries:
            libraries.append(library_path)

    return libraries


def find_steam_app_manifest(app_id, libraries):
    """
    Busca el archivo appmanifest correspondiente a un AppID.

    Devuelve su ruta o None cuando no existe en las bibliotecas conocidas.
    """
    manifest_name = f"appmanifest_{app_id}.acf"

    for library in libraries:
        manifest_file = (
            Path(library)
            / "steamapps"
            / manifest_name
        )

        if manifest_file.is_file():
            return manifest_file

    return None


def parse_steam_app_manifest(manifest_file):
    """
    Lee los metadatos básicos de un appmanifest de Steam.

    Devuelve SteamAppManifest o None si el archivo no existe,
    no puede leerse o no contiene los campos requeridos.
    """
    manifest_file = Path(manifest_file)

    try:
        lines = manifest_file.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines()
    except OSError:
        return None

    values = {}

    for line in lines:
        match = VDF_KEY_VALUE_PATTERN.match(line)

        if match is None:
            continue

        key, value = match.groups()
        normalized_key = key.casefold()

        if normalized_key in {
            "appid",
            "name",
            "installdir",
        }:
            values.setdefault(normalized_key, value)

    try:
        app_id = int(values["appid"])
        name = values["name"].strip()
        install_dir = values["installdir"].strip()
    except (KeyError, ValueError):
        return None

    if not name or not install_dir:
        return None


    library_path = manifest_file.parent.parent

    return SteamAppManifest(
        app_id=app_id,
        name=name,
        install_dir=install_dir,
        manifest_file=str(manifest_file),
        library_path=str(library_path),
    )


def discover_installed_steam_apps(libraryfolders_file):
    """
    Descubre las aplicaciones instaladas en las bibliotecas de Steam.

    Lee todos los appmanifest disponibles y devuelve sus metadatos,
    ordenados por nombre y AppID.
    """

    libraries = discover_steam_libraries(libraryfolders_file)
    applications_by_app_id = {}

    for library in libraries:
        steamapps_directory = Path(library) / "steamapps"

        try:
            manifest_files = steamapps_directory.glob("appmanifest_*.acf")

            for manifest_file in manifest_files:
                manifest = parse_steam_app_manifest(manifest_file)

                if manifest is None:
                    continue

                applications_by_app_id.setdefault(
                    manifest.app_id,
                    manifest,
                )

        except OSError:
            continue

    return sorted(
        applications_by_app_id.values(),
        key=lambda application: (
            application.name.casefold(),
            application.app_id,
        ),
    )


def discover_active_steam_apps(processes, libraryfolders_file):
    """
    Descubre las aplicaciones de Steam actualmente activas.

    Relaciona los lanzamientos detectados en los procesos con las
    bibliotecas configuradas y los metadatos de sus appmanifest.
    """
    launches = discover_steam_launches(processes)
    libraries = discover_steam_libraries(libraryfolders_file)

    active_apps = []

    for launch in launches:
        manifest_file = find_steam_app_manifest(
            launch.app_id,
            libraries,
        )

        if manifest_file is None:
            continue

        manifest = parse_steam_app_manifest(manifest_file)

        if manifest is None:
            continue

        if manifest.app_id != launch.app_id:
            continue

        active_apps.append(
            ActiveSteamApplication(
                launch=launch,
                manifest=manifest,
            )
        )

    return active_apps
