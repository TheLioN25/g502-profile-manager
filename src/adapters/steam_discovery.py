"""
Descubrimiento de aplicaciones ejecutadas mediante Steam.

Este módulo identifica lanzamientos activos de Steam usando la información
expuesta por los procesos supervisores creados durante el lanzamiento,
así como accesos directos de juegos no oficiales (shortcuts.vdf).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import struct


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


@dataclass(frozen=True)
class SteamShortcut:
    app_id: int
    name: str
    exe: str
    start_dir: str = ""
    launch_options: str = ""
    icon: str = ""
    shortcut_path: str = ""


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


def discover_active_steam_apps(processes, libraryfolders_file, shortcuts: list[SteamShortcut] | None = None):
    """
    Descubre las aplicaciones de Steam actualmente activas.

    Relaciona los lanzamientos detectados en los procesos con las
    bibliotecas configuradas y los metadatos de sus appmanifest o shortcuts.vdf.
    """
    launches = discover_steam_launches(processes)
    if not launches:
        return []

    libraries = discover_steam_libraries(libraryfolders_file)

    shortcuts_by_appid: dict[int, SteamShortcut] | None = None
    if shortcuts is not None:
        shortcuts_by_appid = {s.app_id: s for s in shortcuts}

    def _get_shortcuts() -> dict[int, SteamShortcut]:
        nonlocal shortcuts_by_appid
        if shortcuts_by_appid is None:
            try:
                steam_root = Path(libraryfolders_file).parent.parent if Path(libraryfolders_file).exists() else None
                shortcuts_by_appid = {s.app_id: s for s in discover_steam_shortcuts(steam_root=steam_root)}
            except (OSError, ValueError, struct.error):
                shortcuts_by_appid = {}
        return shortcuts_by_appid

    active_apps = []

    for launch in launches:
        manifest_file = find_steam_app_manifest(
            launch.app_id,
            libraries,
        )

        manifest = None
        if manifest_file is not None:
            manifest = parse_steam_app_manifest(manifest_file)

        # Si no existe appmanifest (caso de juegos Non-Steam como Soulframe), resolver desde shortcuts.vdf
        if manifest is None:
            loaded_shortcuts = _get_shortcuts()
            if launch.app_id in loaded_shortcuts:
                shortcut = loaded_shortcuts[launch.app_id]
                manifest = SteamAppManifest(
                    app_id=shortcut.app_id,
                    name=shortcut.name,
                    install_dir=shortcut.start_dir or shortcut.exe,
                    manifest_file="shortcuts.vdf",
                    library_path="",
                )

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


def _clean_vdf_string(val: object) -> str:
    """Elimina espacios y comillas externas de cadenas leídas de shortcuts.vdf."""
    s = str(val or "").strip()
    if len(s) >= 2 and (
        (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'"))
    ):
        s = s[1:-1].strip()
    return s


def parse_binary_vdf(data: bytes) -> dict:
    """
    Decodifica datos en formato Valve Binary KeyValues (shortcuts.vdf).

    Devuelve un diccionario estructurado o {} si los datos están truncados o corruptos.
    """
    if not data:
        return {}

    offset = 0
    length = len(data)

    def read_string() -> str:
        nonlocal offset
        end = data.find(b"\x00", offset)
        if end == -1:
            offset = length
            raise ValueError("Truncated string: missing null terminator")
        val = data[offset:end]
        offset = end + 1
        return val.decode("utf-8", errors="replace")

    def parse_dict() -> dict:
        nonlocal offset
        result = {}
        while offset < length:
            type_byte = data[offset]
            offset += 1
            if type_byte == 8:  # 0x08: Fin de diccionario / bloque
                break
            key = read_string()
            if type_byte == 0:  # 0x00: Sub-diccionario
                result[key] = parse_dict()
            elif type_byte == 1:  # 0x01: String
                result[key] = read_string()
            elif type_byte == 2:  # 0x02: Int32
                if offset + 4 <= length:
                    val = struct.unpack("<I", data[offset:offset + 4])[0]
                    offset += 4
                    result[key] = val
                else:
                    offset = length
                    raise ValueError("Truncated int32")
            elif type_byte == 3:  # 0x03: Float32
                if offset + 4 <= length:
                    val = struct.unpack("<f", data[offset:offset + 4])[0]
                    offset += 4
                    result[key] = val
                else:
                    offset = length
                    raise ValueError("Truncated float32")
            elif type_byte == 7:  # 0x07: Int64
                if offset + 8 <= length:
                    val = struct.unpack("<Q", data[offset:offset + 8])[0]
                    offset += 8
                    result[key] = val
                else:
                    offset = length
                    raise ValueError("Truncated int64")
            else:
                # Tipo desconocido o byte inesperado; abortar para evitar corrupcion de datos
                raise ValueError(f"Unknown VDF type byte: {type_byte} at offset {offset - 1}")
        return result

    try:
        return parse_dict()
    except (OSError, ValueError, struct.error, IndexError):
        return {}


def discover_steam_shortcuts(steam_root: Path | str | None = None) -> list[SteamShortcut]:
    """
    Descubre accesos directos de Steam (Non-Steam Games) en los perfiles de userdata.

    Lee todos los archivos shortcuts.vdf encontrados y devuelve una lista desduplicada
    de objetos SteamShortcut ordenados por nombre y AppID.
    """
    if steam_root is None:
        candidates = [
            Path.home() / ".local/share/Steam",
            Path.home() / ".steam/steam",
            Path.home() / ".steam/root",
        ]
        root_path = None
        for cand in candidates:
            if cand.is_dir():
                root_path = cand
                break
        if root_path is None:
            return []
    else:
        root_path = Path(steam_root).expanduser().resolve()

    userdata_dir = root_path / "userdata"
    if not userdata_dir.is_dir():
        return []

    shortcuts_by_appid: dict[int, SteamShortcut] = {}

    try:
        shortcut_files = list(userdata_dir.glob("*/config/shortcuts.vdf"))
    except OSError:
        return []

    for file_path in shortcut_files:
        try:
            raw_data = file_path.read_bytes()
        except OSError:
            continue

        parsed = parse_binary_vdf(raw_data)
        shortcuts_data = parsed.get("shortcuts")
        if shortcuts_data is None:
            shortcuts_data = parsed.get("Shortcuts", {})
        if not isinstance(shortcuts_data, dict):
            continue

        for key, entry in shortcuts_data.items():
            if not isinstance(entry, dict):
                continue

            app_id_raw = entry.get("appid")
            app_name = _clean_vdf_string(entry.get("AppName"))
            exe = _clean_vdf_string(entry.get("Exe"))

            if not app_name or app_id_raw is None:
                continue

            try:
                app_id = int(app_id_raw) & 0xFFFFFFFF
            except (ValueError, TypeError):
                continue

            if app_id == 0:
                continue

            shortcut = SteamShortcut(
                app_id=app_id,
                name=app_name,
                exe=exe,
                start_dir=_clean_vdf_string(entry.get("StartDir")),
                launch_options=str(entry.get("LaunchOptions") or "").strip(),
                icon=_clean_vdf_string(entry.get("icon")),
                shortcut_path=_clean_vdf_string(entry.get("ShortcutPath")),
            )

            if app_id not in shortcuts_by_appid:
                shortcuts_by_appid[app_id] = shortcut

    return sorted(
        shortcuts_by_appid.values(),
        key=lambda s: (s.name.casefold(), s.app_id),
    )
