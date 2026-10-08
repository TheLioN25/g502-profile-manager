#!/usr/bin/env python3

from dataclasses import dataclass
from pathlib import Path


PROC_DIR = Path("/proc")

IGNORED_NAMES = {
    "systemd",
    "kthreadd",
    "kworker",
    "ksoftirqd",
    "migration",
    "rcu_preempt",
    "watchdog",
    "idle_inject",
}

IGNORED_COMMAND_PARTS = {
    "steamwebhelper",
    "pressure-vessel",
    "srt-bwrap",
    "wineserver",
    "winedevice.exe",
    "plugplay.exe",
    "services.exe",
    "explorer.exe",
    "rpcss.exe",
}


@dataclass(frozen=True)
class ProcessInfo:
    pid: int
    name: str
    executable_path: str
    real_executable_path: str
    command: str

def read_process(pid_path):
    """
    Lee un proceso desde /proc.

    Devuelve ProcessInfo o None si el proceso desaparece,
    no es accesible o no contiene información útil.
    """

    try:
        pid = int(pid_path.name)

        comm_file = pid_path / "comm"
        cmdline_file = pid_path / "cmdline"
        exe_file = pid_path / "exe"

        name = comm_file.read_text(
            encoding="utf-8",
            errors="replace",
        ).strip()

        raw_cmdline = cmdline_file.read_bytes()

        raw_arguments = raw_cmdline.split(b"\x00")

        if raw_arguments and raw_arguments[-1] == b"":
            raw_arguments.pop()

        if not raw_arguments:
            return None

        executable_path = raw_arguments[0].decode(
            "utf-8",
            errors="replace",
        )

        real_executable_path = str(exe_file.resolve())

    except (
        ValueError,
        FileNotFoundError,
        PermissionError,
        ProcessLookupError,
        OSError,
    ):
        return None

    command = (
        raw_cmdline
        .replace(b"\x00", b" ")
        .decode("utf-8", errors="replace")
        .strip()
    )

    if not name:
        return None

    if not command:
        return None

    return ProcessInfo(
        pid=pid,
        name=name,
        executable_path=executable_path,
        real_executable_path=real_executable_path,
        command=command,
    )


def should_ignore(process):
    """
    Descarta procesos del sistema y auxiliares conocidos.
    """

    normalized_name = process.name.casefold()
    normalized_command = process.command.casefold()

    if normalized_name in IGNORED_NAMES:
        return True

    for ignored_part in IGNORED_COMMAND_PARTS:
        if ignored_part in normalized_command:
            return True

    return False


def discover_processes():
    """
    Devuelve procesos accesibles y filtrados desde /proc.
    """

    processes = []

    try:
        entries = PROC_DIR.iterdir()
    except OSError:
        return processes

    for pid_path in entries:

        if not pid_path.name.isdigit():
            continue

        process = read_process(pid_path)

        if process is None:
            continue

        if should_ignore(process):
            continue

        processes.append(process)

    return processes


def deduplicate_processes(processes):
    """
    Elimina procesos repetidos usando nombre + comando.
    """

    unique_processes = {}

    for process in processes:

        key = (
            process.name.casefold(),
            process.command.casefold(),
        )

        if key not in unique_processes:
            unique_processes[key] = process

    return list(unique_processes.values())


def search_processes(query, processes=None):
    """
    Busca texto en el nombre o línea de comandos.
    """

    if processes is None:
        processes = deduplicate_processes(
            discover_processes()
        )

    normalized_query = query.casefold().strip()

    if not normalized_query:
        return processes

    return [
        process
        for process in processes
        if (
            normalized_query in process.name.casefold()
            or normalized_query in process.command.casefold()
        )
]


def get_effective_executable_path(process):
    """
    Devuelve la ruta más útil para identificar el ejecutable.

    Usa la ruta real cuando argv[0] es /proc/self/exe.
    En los demás casos conserva argv[0], necesario para Wine/Proton.
    """

    if process.executable_path == "/proc/self/exe":
        return process.real_executable_path

    return process.executable_path


def extract_executable_name(process):
    """
    Extrae el nombre del ejecutable desde argv[0].

    Soporta rutas Linux y rutas Windows usadas por Wine/Proton,
    incluso cuando contienen espacios.
    """

    return (
        get_effective_executable_path(process)
        .replace("\\", "/")
        .rsplit("/", maxsplit=1)[-1]
    )


def process_name_is_running(process_name, processes=None):
    """
    Comprueba si existe un proceso cuyo ejecutable real coincide
    con el nombre configurado.

    Soporta rutas Linux y rutas Windows usadas por Wine/Proton.
    """

    if processes is None:
        processes = discover_processes()

    normalized_name = process_name.casefold().strip()

    for process in processes:
        executable_name = extract_executable_name(process)

        if executable_name.casefold() == normalized_name:
            return True

    return False

def print_processes(processes):
    """
    Imprime procesos de forma legible para las pruebas.
    """

    if not processes:
        print("No se encontraron procesos.")
        return

    for process in sorted(
        processes,
        key=lambda item: item.name.casefold(),
    ):
        print(f"PID: {process.pid}")
        print(f"Nombre: {process.name}")
        print(f"Comando: {process.command}")
        print("-" * 60)


def main():
    processes = deduplicate_processes(
        discover_processes()
    )

    print("G502 Profile Manager - Process Discovery")
    print("----------------------------------------")
    print(f"Procesos candidatos encontrados: {len(processes)}")
    print()

    print_processes(processes)


if __name__ == "__main__":
    main()
