"""
Resolución de aplicaciones activas para G502 Profile Manager.

Este módulo relaciona procesos en ejecución con aplicaciones instaladas
descubiertas mediante archivos .desktop, alias conocidos y heurística de subárbol.
"""

from __future__ import annotations

from dataclasses import dataclass
import shlex
from typing import Mapping

from .desktop_entries import DesktopEntry
from .process_discovery import ProcessInfo, extract_executable_name


@dataclass(frozen=True)
class ActiveApplication:
    name: str
    application_id: str
    source: str
    executable: str
    desktop_files: tuple[str, ...]
    process_ids: tuple[int, ...]
    ambiguous: bool


def build_desktop_entry_index(desktop_entries, alias_map=None):
    """
    Agrupa DesktopEntry por nombre de ejecutable, clase de ventana (StartupWMClass)
    y alias o binarios secundarios conocidos (ej. Soulframe.x64.exe).

    Un mismo ejecutable o StartupWMClass puede pertenecer a varias entradas .desktop.
    """
    entries_by_executable = {}

    # Construir mapa invertido de canonical_key -> set de alias
    canonical_to_aliases: dict[str, set[str]] = {}
    if alias_map and isinstance(alias_map, dict):
        for alias, target in alias_map.items():
            if isinstance(target, str):
                canonical_to_aliases.setdefault(target.casefold(), set()).add(alias.casefold())

    for entry in desktop_entries:
        if not isinstance(entry, DesktopEntry):
            raise TypeError(
                "desktop_entries debe contener instancias de DesktopEntry."
            )

        key = entry.executable.casefold()
        entries_by_executable.setdefault(key, []).append(entry)

        if entry.startup_wm_class:
            wm_key = entry.startup_wm_class.casefold()
            if wm_key != key:
                entries_by_executable.setdefault(wm_key, []).append(entry)

        # Enlazar alias y binarios secundarios asociados a esta entrada
        if alias_map and canonical_to_aliases:
            candidates = [key, f"desktop:{key}"]
            if entry.startup_wm_class:
                candidates.extend([entry.startup_wm_class.casefold(), f"desktop:{entry.startup_wm_class.casefold()}"])

            GENERIC_LAUNCHER_NAMES = {"launcher.exe", "desktop:launcher.exe", "start.exe", "game.exe"}

            for cand in candidates:
                canonical = alias_map.get(cand)
                if canonical and canonical.casefold() in canonical_to_aliases:
                    cand_lower = cand.casefold()
                    if cand_lower in GENERIC_LAUNCHER_NAMES:
                        context = f"{entry.name} {entry.desktop_file} {entry.exec_value}".casefold()
                        if canonical.casefold() not in context:
                            continue

                    for related_alias in canonical_to_aliases[canonical.casefold()]:
                        clean_alias = related_alias.replace("desktop:", "").replace("steam:", "").strip()
                        if clean_alias and clean_alias != key:
                            entries = entries_by_executable.setdefault(clean_alias, [])
                            if entry not in entries:
                                entries.append(entry)
                    break

    return entries_by_executable


def resolve_active_applications(processes, desktop_entries, alias_map=None):
    """
    Relaciona procesos en ejecución con entradas .desktop.

    Agrupa todos los procesos que comparten ejecutable y conserva
    las posibles entradas .desktop asociadas utilizando coincidencia directa,
    alias secundarios y heurística por subárbol de instalación.
    """
    entries_by_executable = build_desktop_entry_index(desktop_entries, alias_map=alias_map)
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

    # Identificar árboles de instalación conocidos de juegos para la heurística de subárbol
    GENERIC_CONTAINER_NAMES = {
        "program files",
        "program files (x86)",
        "drive_c",
        "windows",
        "system32",
        "users",
        "appdata",
        "games",
        "steamapps",
        "common",
        "wine",
        "pfx",
        "prefix",
        "compatdata",
        "dosdevices",
    }

    game_install_trees: list[tuple[str, DesktopEntry]] = []
    for entry in desktop_entries:
        if getattr(entry, "is_game", False) and entry.exec_value:
            try:
                tokens = shlex.split(entry.exec_value)
            except ValueError:
                tokens = entry.exec_value.split()

            for tok in tokens:
                clean = tok.replace("\\", "/").strip().strip('"').strip("'")
                if clean.lower().endswith((".exe", ".bin", ".lnk", ".sh")) and "/" in clean:
                    exe_dir = clean.rsplit("/", 1)[0].casefold()
                    base_dir_name = exe_dir.rsplit("/", 1)[-1] if "/" in exe_dir else exe_dir
                    if len(exe_dir) >= 8 and base_dir_name not in GENERIC_CONTAINER_NAMES:
                        if (exe_dir, entry) not in game_install_trees:
                            game_install_trees.append((exe_dir, entry))

    active_applications = []

    for key, process_group in processes_by_executable.items():
        matched_entries = list(entries_by_executable.get(key, []))

        # Si no hubo coincidencia por ejecutable ni alias, aplicar heurística por subárbol
        if not matched_entries and game_install_trees:
            for proc in process_group["processes"]:
                full_cmd = f"{proc.executable_path} {proc.command}".replace("\\", "/").casefold()
                for tree_dir, entry in game_install_trees:
                    if tree_dir in full_cmd and entry not in matched_entries:
                        matched_entries.append(entry)

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

        primary_entry = matched_entries[0]
        app_id = f"desktop:{primary_entry.executable.casefold()}" if primary_entry.executable else process_group["executable"]

        active_applications.append(
            ActiveApplication(
                name=" / ".join(names),
                application_id=app_id,
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

    from .steam_discovery import ActiveSteamApplication

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


def combine_active_applications(application_groups):
    """
    Combina aplicaciones activas procedentes de distintas fuentes.

    Conserva una única aplicación por source + application_id.
    """

    applications_by_identity = {}

    for application_group in application_groups:
        for application in application_group:
            if not isinstance(application, ActiveApplication):
                raise TypeError(
                    "application_groups debe contener instancias "
                    "de ActiveApplication."
                )

            key = (
                application.source.casefold(),
                application.application_id.casefold(),
            )

            applications_by_identity.setdefault(
                key,
                application,
            )

    return sorted(
        applications_by_identity.values(),
        key=lambda application: (
            application.name.casefold(),
            application.source.casefold(),
            application.application_id.casefold(),
        ),
    )
