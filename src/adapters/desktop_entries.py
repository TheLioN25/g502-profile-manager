"""
Descubrimiento de aplicaciones gráficas instaladas en Linux.

Este módulo lee archivos .desktop y extrae información básica
que posteriormente utilizará el clasificador de procesos.
"""

from dataclasses import dataclass
from pathlib import Path
import configparser
import shlex

DESKTOP_DIRECTORIES = (
    Path.home() / ".local/share/applications",
    Path("/usr/local/share/applications"),
    Path("/usr/share/applications"),
)


@dataclass(frozen=True)
class DesktopEntry:
    name: str
    executable: str
    exec_value: str
    desktop_file: str
    startup_wm_class: str | None = None
    is_game: bool = False


def extract_exec_name(exec_value, startup_wm_class: str | None = None):
    """
    Extrae el nombre del ejecutable desde el campo Exec de un archivo .desktop.

    Soporta comandos directos, comandos env con asignaciones
    de variables de entorno y comandos de emulación Wine/Proton.
    """

    if not exec_value:
        return None

    try:
        tokens = shlex.split(exec_value)
    except ValueError:
        return None

    if not tokens:
        return None

    if tokens[0] == "env":
        tokens = tokens[1:]

        while tokens and "=" in tokens[0]:
            tokens = tokens[1:]

        if not tokens:
            return None

    binary_name = Path(tokens[0]).name

    # Si la invocación se realiza a través de Wine, resolver el ejecutable destino
    if binary_name.lower() in ("wine", "wine64"):
        if startup_wm_class:
            return startup_wm_class

        for token in tokens[1:]:
            clean = token.replace("\\", "/").rstrip("/").split("/")[-1]
            if not clean:
                continue
            lower = clean.lower()
            if lower.endswith((".exe", ".bat", ".cmd")):
                return clean
            if lower.endswith(".lnk"):
                return clean[:-4]

    return binary_name


def parse_desktop_entry(desktop_file, lang: str | None = None):
    """
    Lee un archivo .desktop y devuelve un DesktopEntry.

    Ignora archivos inválidos, entradas ocultas y entradas que no
    contienen Name o Exec.
    """

    parser = configparser.ConfigParser(
        interpolation=None,
        strict=False,
    )

    try:
        parser.read(desktop_file, encoding="utf-8")
    except (OSError, UnicodeError, configparser.Error):
        return None

    if "Desktop Entry" not in parser:
        return None

    entry = parser["Desktop Entry"]

    if entry.getboolean("Hidden", fallback=False):
        return None

    if entry.getboolean("NoDisplay", fallback=False):
        return None

    exec_value = entry.get("Exec", "").strip()
    if not exec_value:
        return None

    startup_wm_class = entry.get("StartupWMClass", "").strip() or None

    executable = extract_exec_name(exec_value, startup_wm_class=startup_wm_class)
    if not executable:
        return None

    # Resolución de nombre localizado según idioma (estándar FreeDesktop XDG)
    target_lang = lang
    if target_lang is None:
        try:
            from i18n import get_language
            target_lang = get_language()
        except Exception:
            import os
            target_lang = "es" if os.environ.get("LANG", "").lower().startswith("es") else "en"

    name = None
    if target_lang == "es":
        # Priorizar variantes en español: Name[es_XX], Name[es]
        for key in entry.keys():
            if key.lower().startswith("name[es"):
                name = entry[key].strip()
                break
    elif target_lang == "en":
        # Priorizar variantes en inglés: Name[en_XX], Name[en]
        for key in entry.keys():
            if key.lower().startswith("name[en"):
                name = entry[key].strip()
                break

    # Fallback al Name estándar (por especificación XDG es siempre inglés/neutral)
    if not name:
        name = entry.get("Name", "").strip()

    if not name:
        return None

    categories = entry.get("Categories", "")
    categories_list = [c.strip().lower() for c in categories.split(";") if c.strip()]
    file_str = str(desktop_file).lower()
    exec_lower = exec_value.lower()
    exec_base = Path(executable).name.lower() if executable else ""

    WINE_UTILITIES = {
        "winecfg",
        "winecfg.exe",
        "winetricks",
        "wineboot",
        "wineboot.exe",
        "winefile",
        "winefile.exe",
        "winepath",
        "wineserver",
        "uninstaller",
        "uninstaller.exe",
        "control",
        "control.exe",
        "regedit",
        "regedit.exe",
        "notepad",
        "notepad.exe",
        "wordpad",
        "wordpad.exe",
        "oleview",
        "oleview.exe",
    }
    is_wine_utility = exec_base in WINE_UTILITIES or any(
        u in exec_lower for u in ("winecfg", "winetricks", "wineboot", "uninstaller.exe")
    )

    is_game = False
    if not is_wine_utility:
        is_game = (
            "game" in categories_list
            or "/steam/" in file_str
            or "proton" in file_str
            or "proton" in exec_lower
            or (exec_base.endswith(".exe") and ("wine" in exec_lower or "/wine/" in file_str))
        )

    return DesktopEntry(
        name=name,
        executable=executable,
        exec_value=exec_value,
        desktop_file=str(desktop_file),
        startup_wm_class=startup_wm_class,
        is_game=is_game,
    )


def discover_desktop_entries(directories=DESKTOP_DIRECTORIES):
    """
    Descubre archivos .desktop instalados en el sistema de forma recursiva.

    Devuelve sus rutas desduplicadas preservando el orden.
    """

    desktop_files = []
    seen = set()

    for directory in directories:
        dir_path = Path(directory)
        if not dir_path.is_dir():
            continue

        for file_path in dir_path.rglob("*.desktop"):
            if file_path.is_file() and file_path not in seen:
                seen.add(file_path)
                desktop_files.append(file_path)

    return desktop_files
