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


def parse_desktop_entry(desktop_file):
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

    name = entry.get("Name", "").strip()
    exec_value = entry.get("Exec", "").strip()

    if not name or not exec_value:
        return None

    executable = extract_exec_name(exec_value)

    if not executable:
        return None

    return DesktopEntry(
        name=name,
        executable=executable,
        exec_value=exec_value,
        desktop_file=str(desktop_file),
    )


def discover_desktop_entries():
    """
    Descubre archivos .desktop instalados en el sistema.

    Por ahora devuelve únicamente sus rutas.
    """

    desktop_files = []

    for directory in DESKTOP_DIRECTORIES:
        if not directory.is_dir():
            continue

        desktop_files.extend(directory.glob("*.desktop"))

    return desktop_files
