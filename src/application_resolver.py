"""
Resolución de aplicaciones activas para G502 Profile Manager.

Este módulo relaciona procesos en ejecución con aplicaciones instaladas
descubiertas mediante archivos .desktop.
"""

from dataclasses import dataclass

from desktop_entries import DesktopEntry
from process_discovery import ProcessInfo, extract_executable_name


@dataclass(frozen=True)
class ActiveApplication:
    name: str
    application_id: str
    source: str
    executable: str
    desktop_files: tuple[str, ...]
    process_ids: tuple[int, ...]
    ambiguous: bool


def build_desktop_entry_index(desktop_entries):
    """
    Agrupa DesktopEntry por nombre de ejecutable.

    Un mismo ejecutable puede pertenecer a varias entradas .desktop.
    """

    entries_by_executable = {}

    for entry in desktop_entries:
        if not isinstance(entry, DesktopEntry):
            raise TypeError(
                "desktop_entries debe contener instancias de DesktopEntry."
            )

        key = entry.executable.casefold()
        entries_by_executable.setdefault(key, []).append(entry)

    return entries_by_executable


def resolve_active_applications(processes, desktop_entries):
    """
    Relaciona procesos en ejecución con entradas .desktop.

    Agrupa todos los procesos que comparten ejecutable y conserva
    las posibles entradas .desktop asociadas.
    """

    entries_by_executable = build_desktop_entry_index(desktop_entries)
    processes_by_executable = {}

    for process in processes:
        if not isinstance(process, ProcessInfo):
            raise TypeError(
                "processes debe contener instancias de ProcessInfo."
            )

        executable = extract_executable_name(process)
        key = executable.casefold()

        processes_by_executable.setdefault(
            key,
            {
                "executable": executable,
                "processes": [],
            },
        )

        processes_by_executable[key]["processes"].append(process)

    active_applications = []

    for key, process_group in processes_by_executable.items():
        matched_entries = entries_by_executable.get(key, [])

        if not matched_entries:
            continue

        names = tuple(
            sorted({
                entry.name
                for entry in matched_entries
            })
        )

        desktop_files = tuple(
            sorted({
                entry.desktop_file
                for entry in matched_entries
            })
        )

        process_ids = tuple(
            sorted({
                process.pid
                for process in process_group["processes"]
            })
        )

        active_applications.append(
            ActiveApplication(
                name=" / ".join(names),
                application_id=process_group["executable"],
                source="desktop",
                executable=process_group["executable"],
                desktop_files=desktop_files,
                process_ids=process_ids,
                ambiguous=len(names) > 1,
            )
        )

    return sorted(
        active_applications,
        key=lambda application: (
            application.name.casefold(),
            application.executable.casefold(),
        ),
    )


def resolve_steam_applications(steam_applications):
    """
    Convierte aplicaciones Steam activas al modelo ActiveApplication.
    """

    from steam_discovery import ActiveSteamApplication

    active_applications = []

    for steam_application in steam_applications:
        if not isinstance(steam_application, ActiveSteamApplication):
            raise TypeError(
                "steam_applications debe contener instancias "
                "de ActiveSteamApplication."
            )

        launch = steam_application.launch
        manifest = steam_application.manifest

        active_applications.append(
            ActiveApplication(
                name=manifest.name,
                application_id=f"steam:{manifest.app_id}",
                source="steam",
                executable="",
                desktop_files=(),
                process_ids=(launch.supervisor_pid,),
                ambiguous=False,
            )
        )

    return sorted(
        active_applications,
        key=lambda application: (
            application.name.casefold(),
            application.application_id.casefold(),
        ),
    )
