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


def extract_exec_name(exec_value):
    """
    Extrae el nombre del ejecutable desde el campo Exec de un archivo .desktop.

    Soporta comandos directos y comandos env con asignaciones
    de variables de entorno antes del ejecutable real.
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

    return Path(tokens[0]).name


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

    executable = extract_exec_name(exec_value)
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

    return DesktopEntry(
        name=name,
        executable=executable,
        exec_value=exec_value,
        desktop_file=str(desktop_file),
    )


def discover_desktop_entries(directories=DESKTOP_DIRECTORIES):
    """
    Descubre archivos .desktop instalados en el sistema.

    Por ahora devuelve únicamente sus rutas.
    """

    desktop_files = []

    for directory in directories:
        dir_path = Path(directory)
        if not dir_path.is_dir():
            continue

        desktop_files.extend(dir_path.glob("*.desktop"))

    return desktop_files
