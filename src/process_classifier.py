"""
Clasificación de procesos para G502 Profile Manager.

Este módulo transforma procesos descubiertos por process_discovery
en candidatos que podrán ser mostrados en la interfaz gráfica.
"""

from dataclasses import dataclass
from process_discovery import ProcessInfo, extract_executable_name

@dataclass(frozen=True)
class ProcessCandidate:
    pid: int
    name: str
    command: str
    executable: str
    category: str
    score: int

WINDOWS_HELPER_EXECUTABLES = frozenset({
    "steam.exe",
    "svchost.exe",
    "tabtip.exe",
    "services.exe",
    "explorer.exe",
    "plugplay.exe",
    "winedevice.exe",
    "wineboot.exe",
    "rpcss.exe",
    "conhost.exe",
})

def uses_windows_path(process):
    """
    Comprueba si argv[0] parece ser una ruta Windows.

    Ejemplos:
    C:\\Games\\Game.exe
    S:\\common\\Warframe\\Warframe.x64.exe
    """

    executable_path = process.executable_path

    return (
        len(executable_path) >= 3
        and executable_path[0].isalpha()
        and executable_path[1] == ":"
        and executable_path[2] in ("\\", "/")
    )

def is_known_windows_helper(process):
    """
    Comprueba si el ejecutable pertenece a un proceso auxiliar conocido
    de Wine, Proton o Steam.
    """

    executable = extract_executable_name(process).casefold()

    return executable in WINDOWS_HELPER_EXECUTABLES


def calculate_process_score(process):
    """
    Calcula una puntuación inicial de relevancia.

    Una puntuación alta indica que el proceso tiene más posibilidades
    de ser útil para el usuario en la interfaz.
    """

    score = 0

    if uses_windows_path(process):
        score += 40

    if is_known_windows_helper(process):
        score -= 100

    return score

def classify_process(process):
    """
    Convierte un ProcessInfo en un ProcessCandidate.

    Por ahora no aplica reglas de clasificación.
    """

    if not isinstance(process, ProcessInfo):
        raise TypeError("process debe ser una instancia de ProcessInfo.")

    executable = extract_executable_name(process)
    score = calculate_process_score(process)

    if is_known_windows_helper(process):
    	category = "helper"
    elif uses_windows_path(process):
    	category = "windows_application"
    else:
    	category = "unknown"

    return ProcessCandidate(
    	pid=process.pid,
    	name=process.name,
    	command=process.command,
    	executable=executable,
    	category=category,
    	score=score,
)
