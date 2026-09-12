#!/usr/bin/env python3
"""
Interfaz de línea de comandos unificada (CLI) para G502 Profile Manager.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

# Asegurar importaciones relativas
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from adapters import (
    ApplicationDiscoveryAdapter,
    RatbagDeviceAdapter,
    get_preset_actions_for_application,
    populate_application_actions,
)
from domain import Action, Button, DpiConfiguration
from engine import AutomationEngine, DEFAULT_PROFILES_FILE
from services import ProfileManager
from storage import JsonProfileRepository


def get_services():
    repo = JsonProfileRepository(DEFAULT_PROFILES_FILE)
    manager = ProfileManager(repo)
    discovery = ApplicationDiscoveryAdapter()
    adapter = RatbagDeviceAdapter()
    return repo, manager, discovery, adapter


def cmd_list(args):
    _, manager, discovery, _ = get_services()

    print("\nDescubriendo aplicaciones instaladas...")
    apps = discovery.discover_all_applications()

    total = len(apps)
    configured_apps = [
        app for app in apps if manager.get_profiles_for_application(app.application_id)
    ]

    print("==================================================")
    print(f" Total detectadas: {total} | Con perfiles: {len(configured_apps)}")
    print("==================================================\n")

    for app in apps:
        profiles = manager.get_profiles_for_application(app.application_id)
        if profiles:
            default_prof = manager.get_default_profile(app.application_id)
            default_str = f" [Predeterminado: '{default_prof.name}']" if default_prof else ""
            print(f"[X] {app.name} ({app.application_id})")
            print(f"    Perfiles configurados: {len(profiles)}{default_str}")
            for p in profiles:
                print(f"      - ID: {p.id[:8]}.. | '{p.name}' | DPI: {p.dpi.dpi} | Asignaciones: {len(p.list_assignments())}")
        else:
            has_presets = len(get_preset_actions_for_application(app.application_id)) > 0
            preset_str = " (Presets disponibles)" if has_presets else ""
            print(f"[ ] {app.name} ({app.application_id}){preset_str}")


def cmd_profiles(args):
    repo, manager, _, _ = get_services()
    all_profiles = repo.list_all()

    print("\nPerfiles guardados en el sistema:")
    print("==================================")
    if not all_profiles:
        print("No hay perfiles creados todavía. Usa 'g502-profile create' para crear uno.")
        return

    for p in all_profiles:
        is_default = manager.get_default_profile(p.application_id)
        tag = " [PREDETERMINADO]" if is_default and is_default.id == p.id else ""
        led = f" | LED: {p.led_color}" if p.led_color else ""
        print(f"• ID: {p.id}")
        print(f"  Nombre: '{p.name}'{tag}")
        print(f"  Aplicación: {p.application_id}")
        print(f"  DPI: {p.dpi.dpi}{led}")
        print(f"  Asignaciones ({len(p.list_assignments())}):")
        for assign in p.list_assignments():
            print(f"    - {assign.button.button_id} ({assign.button.name}) -> {assign.action.name} [{assign.action.binding_value}]")
        print()


def cmd_create(args):
    _, manager, _, _ = get_services()

    dpi_config = DpiConfiguration(dpi=args.dpi, shift_dpi=args.shift_dpi)
    profile = manager.create_profile(
        name=args.name,
        application_id=args.app_id,
        dpi=dpi_config,
        led_color=args.led,
    )

    print(f"\nPerfil '{profile.name}' creado exitosamente.")
    print(f"ID: {profile.id}")
    print(f"Aplicación: {profile.application_id}")
    print(f"DPI: {profile.dpi.dpi}")
    if profile.led_color:
        print(f"Color LED: {profile.led_color}")


def cmd_presets(args):
    presets = get_preset_actions_for_application(args.app_id)
    if not presets:
        print(f"No hay presets predefinidos para '{args.app_id}'.")
        return

    print(f"\nAcciones predefinidas disponibles para '{args.app_id}':")
    print("=========================================================")
    for a in presets:
        print(f"• {a.action_id}: {a.name} -> Tecla: '{a.binding_value}' ({a.description})")


def cmd_assign(args):
    repo, manager, _, _ = get_services()
    profile = manager.get_profile(args.profile_id)
    if not profile:
        # Buscar por prefijo de ID
        matching = [p for p in repo.list_all() if p.id.startswith(args.profile_id)]
        if len(matching) == 1:
            profile = matching[0]
        else:
            print(f"Error: No se encontró el perfil con ID '{args.profile_id}'.")
            return

    button = Button(button_id=args.button.upper(), name=f"Botón {args.button.upper()}")

    # Verificar si coincide con un preset
    presets = get_preset_actions_for_application(profile.application_id)
    preset_match = next((p for p in presets if p.action_id == args.action_id), None)

    if preset_match:
        action = preset_match
    else:
        action_name = args.name or args.action_id
        action = Action(
            action_id=args.action_id,
            name=action_name,
            application_id=profile.application_id,
            binding_type="key",
            binding_value=args.key or args.action_id,
        )

    manager.assign_button(profile.id, button, action)
    print(f"Asignación guardada: {button.button_id} -> {action.name} ['{action.binding_value}'] en perfil '{profile.name}'.")


def cmd_reset(args):
    repo, manager, _, _ = get_services()
    profile = manager.get_profile(args.profile_id)
    if not profile:
        matching = [p for p in repo.list_all() if p.id.startswith(args.profile_id)]
        if len(matching) == 1:
            profile = matching[0]
        else:
            print(f"Error: No se encontró el perfil con ID '{args.profile_id}'.")
            return

    manager.reset_profile(profile.id)
    print(f"Asignaciones del perfil '{profile.name}' restablecidas a estado limpio.")


def cmd_run(args):
    repo, manager, _, adapter = get_services()
    engine = AutomationEngine(
        profile_manager=manager,
        device_adapter=adapter,
        check_interval=args.interval,
    )
    engine.run()


def create_parser():
    parser = argparse.ArgumentParser(
        prog="g502-profile",
        description="Administrador automático y manual de perfiles para Logitech G502 HERO.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="g502-profile 0.3.0",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # list
    subparsers.add_parser("list", help="Lista aplicaciones instaladas y su estado de configuración.")

    # profiles
    subparsers.add_parser("profiles", help="Lista los perfiles guardados y sus asignaciones.")

    # create
    create_p = subparsers.add_parser("create", help="Crea un nuevo perfil para una aplicación.")
    create_p.add_argument("app_id", help="Identificador de la aplicación (ej. steam:230410).")
    create_p.add_argument("name", help="Nombre del perfil (ej. 'Saryn DPS').")
    create_p.add_argument("--dpi", type=int, default=1200, help="Sensibilidad DPI principal (ej. 1200).")
    create_p.add_argument("--shift-dpi", type=int, default=None, help="DPI para botón sniper.")
    create_p.add_argument("--led", default=None, help="Color LED en hexadecimal (ej. '#00E5FF').")

    # presets
    preset_p = subparsers.add_parser("presets", help="Muestra las acciones predefinidas para una aplicación.")
    preset_p.add_argument("app_id", help="Identificador de la aplicación (ej. steam:230410).")

    # assign
    assign_p = subparsers.add_parser("assign", help="Asigna una acción a un botón del ratón.")
    assign_p.add_argument("profile_id", help="ID o prefijo del perfil.")
    assign_p.add_argument("button", help="Botón del mouse (G4, G5, SNIPER, G7, G8, G9, etc.).")
    assign_p.add_argument("action_id", help="ID de la acción o preset (ej. wf_ability_1).")
    assign_p.add_argument("--key", default="", help="Tecla a enviar si es una acción personalizada.")
    assign_p.add_argument("--name", default="", help="Nombre descriptivo de la acción personalizada.")

    # reset
    reset_p = subparsers.add_parser("reset", help="Vacía las asignaciones de un perfil.")
    reset_p.add_argument("profile_id", help="ID o prefijo del perfil.")

    # run / engine
    run_p = subparsers.add_parser("run", help="Inicia el motor de automatización en tiempo real.")
    run_p.add_argument("--interval", type=float, default=2.0, help="Intervalo de chequeo en segundos.")

    engine_p = subparsers.add_parser("engine", help="Alias para 'run'.")
    engine_p.add_argument("--interval", type=float, default=2.0, help="Intervalo de chequeo en segundos.")

    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()

    handlers = {
        "list": cmd_list,
        "profiles": cmd_profiles,
        "create": cmd_create,
        "presets": cmd_presets,
        "assign": cmd_assign,
        "reset": cmd_reset,
        "run": cmd_run,
        "engine": cmd_run,
    }

    handler = handlers.get(args.command)
    if handler:
        handler(args)


if __name__ == "__main__":
    main()