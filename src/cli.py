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
from services import ActionCatalogService, ProfileManager
from storage import JsonProfileRepository


def get_services():
    repo = JsonProfileRepository(DEFAULT_PROFILES_FILE)
    manager = ProfileManager(repo)
    discovery = ApplicationDiscoveryAdapter()
    adapter = RatbagDeviceAdapter()
    catalog = ActionCatalogService()
    return repo, manager, discovery, adapter, catalog


def cmd_list(args):
    _, manager, discovery, _, catalog = get_services()

    print("\nDescubriendo aplicaciones instaladas...")
    desktop_apps = discovery.discover_desktop_applications()
    steam_apps = discovery.discover_steam_applications()
    all_apps = discovery.combine_discovered(desktop_apps, steam_apps)

    print(f"Total aplicaciones detectadas: {len(all_apps)}\n")
    for app in all_apps:
        profiles = manager.get_profiles_for_application(app.application_id)
        has_preset = "✓ Presets disponibles" if catalog.has_catalog(app.application_id) else "—"
        print(f"• [{app.application_id}] {app.name}")
        print(f"  Ejecutable: {app.executable_or_path}")
        print(f"  Perfiles: {len(profiles)} configurados | {has_preset}")
        print()


def cmd_profiles(args):
    repo, _, _, _, _ = get_services()
    profiles = repo.list_all()

    if not profiles:
        print("\nNo hay perfiles configurados.")
        print("Crea uno nuevo con: g502-profile create <app_id> <name>\n")
        return

    print(f"\nPerfiles configurados ({len(profiles)}):")
    print("=========================================")
    for p in profiles:
        is_default = repo.get_default_profile_id(p.application_id) == p.id
        tag = " [PREDETERMINADO]" if is_default else ""
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
    _, manager, _, _, catalog = get_services()

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

    # Indicar si el catálogo cargó acciones disponibles
    actions = catalog.get_actions_for_application(args.app_id)
    if actions:
        categories = catalog.get_categories_for_application(args.app_id)
        print(f"\nCatálogo disponible: {len(actions)} acciones en {len(categories)} categorías.")
        print(f"Usa 'g502-profile presets {args.app_id}' para ver todas las acciones asignables.")


def cmd_presets(args):
    _, _, discovery, _, catalog = get_services()

    # Sincronizar catálogo al vuelo con aplicaciones instaladas en Steam y Epic Games
    installed_apps = discovery.discover_all_applications()
    catalog.sync_with_installed_applications(installed_apps)
    installed_ids = {a.application_id for a in installed_apps}

    if not args.app_id or args.app_id.strip() == "list":
        # Mostrar únicamente las aplicaciones con catálogo instaladas en tu equipo
        catalogs = catalog.list_supported_applications(installed_app_ids=installed_ids)
        print("\nJuegos y aplicaciones con catálogo de acciones (detectados en tu sistema):")
        print("=========================================================================")
        for cat in catalogs:
            print(f"• [{cat['application_id']}] {cat['name']} ({cat['action_count']} acciones)")
            if cat['description']:
                print(f"  {cat['description']}")
        print("\nPara ver el detalle de un juego: g502-profile presets <app_id>\n")
        return

    categories = catalog.get_categories_for_application(args.app_id)
    if not categories:
        print(f"No hay catálogo predefinido para '{args.app_id}'.")
        print(f"Puedes agregar acciones personalizadas con: g502-profile add-action {args.app_id} <action_id> <name> <key>")
        return

    app_name = catalog.get_application_name(args.app_id) or args.app_id
    total_actions = sum(len(acts) for acts in categories.values())

    print(f"\nCatálogo de acciones para '{app_name}' ({args.app_id}) - {total_actions} acciones:")
    print("================================================================================")
    for category_name, actions in categories.items():
        print(f"\n[{category_name.upper()}]")
        for a in actions:
            val = f"'{a.binding_value}'" if a.binding_value else "(sin asignar)"
            desc = f" — {a.description}" if a.description else ""
            print(f"  • {a.action_id:<22} : {a.name:<25} -> {val:<15} ({a.binding_type}){desc}")
    print()


def cmd_add_action(args):
    _, _, _, _, catalog = get_services()

    action = Action(
        action_id=args.action_id,
        name=args.name,
        application_id=args.app_id,
        description=args.desc,
        binding_type=args.type,
        binding_value=args.key,
        category=args.category,
    )

    success = catalog.register_custom_action(
        application_id=args.app_id,
        action=action,
        persist_user_preset=True,
    )

    if success:
        print(f"\nAcción personalizada '{action.name}' añadida con éxito a '{args.app_id}'.")
        print(f"Categoría: {action.category} | Tecla: '{action.binding_value}' | Tipo: {action.binding_type}")
        print(f"Persistida en ~/.config/g502-profile-manager/presets/\n")
    else:
        print(f"Error al registrar la acción personalizada.")


def cmd_assign(args):
    repo, manager, _, _, catalog = get_services()
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

    # presets / catalog
    preset_p = subparsers.add_parser("presets", help="Muestra las acciones predefinidas para una aplicación.")
    preset_p.add_argument("app_id", nargs="?", default="list", help="Identificador de la aplicación o vacío para ver todos.")

    catalog_p = subparsers.add_parser("catalog", help="Alias para 'presets'.")
    catalog_p.add_argument("app_id", nargs="?", default="list", help="Identificador de la aplicación o vacío para ver todos.")

    # add-action
    add_action_p = subparsers.add_parser("add-action", help="Añade una acción personalizada para una aplicación.")
    add_action_p.add_argument("app_id", help="Identificador de la aplicación (ej. steam:230410).")
    add_action_p.add_argument("action_id", help="ID único de la acción (ej. mi_atajo).")
    add_action_p.add_argument("name", help="Nombre descriptivo (ej. 'Disparo Secundario').")
    add_action_p.add_argument("key", help="Tecla o código de entrada (ej. 'e', 'space').")
    add_action_p.add_argument("--category", default="Personalizado", help="Categoría de la acción (ej. Combate).")
    add_action_p.add_argument("--desc", default="", help="Descripción detallada de la acción.")
    add_action_p.add_argument("--type", default="key", choices=["key", "macro", "special"], help="Tipo de binding.")

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

    # gui
    subparsers.add_parser("gui", help="Inicia la interfaz gráfica nativa (GTK4 + Libadwaita).")

    # desktop integration
    subparsers.add_parser("install-desktop", help="Instala el acceso directo y su icono en el menú de aplicaciones del sistema.")
    subparsers.add_parser("uninstall-desktop", help="Desinstala el acceso directo y su icono del sistema.")

    return parser


def cmd_gui(args):
    try:
        from gui.app import G502Application
        app = G502Application()
        return app.run(sys.argv[:1])
    except ImportError as e:
        print(f"Error al iniciar la interfaz gráfica: {e}")
        print("Asegúrate de tener instalados GTK4 y Libadwaita (python-gi, libadwaita-1).")
        return 1


def cmd_install_desktop(args):
    import shutil
    import subprocess

    repo_root = Path(__file__).resolve().parent.parent
    desktop_dest_dir = Path.home() / ".local/share/applications"
    icons_dest_dir = Path.home() / ".local/share/icons/hicolor/scalable/apps"

    desktop_dest_dir.mkdir(parents=True, exist_ok=True)
    icons_dest_dir.mkdir(parents=True, exist_ok=True)

    src_icon = repo_root / "data" / "icons" / "io.github.thelion.G502ProfileManager.svg"
    dest_icon = icons_dest_dir / "io.github.thelion.G502ProfileManager.svg"
    if src_icon.exists():
        shutil.copy2(src_icon, dest_icon)
        print(f"• Icono instalado: {dest_icon}")

    desktop_content = f"""[Desktop Entry]
Name=G502 Profile Manager
GenericName=Gestor de Ratón Logitech G502 HERO
Comment=Gestor nativo de perfiles, macros, DPI e iluminación para ratón Logitech G502 HERO en Linux
Exec={sys.executable} {repo_root / 'src/cli.py'} gui
Icon=io.github.thelion.G502ProfileManager
Terminal=false
Type=Application
Categories=Settings;HardwareSettings;Game;Utility;
Keywords=Logitech;G502;Mouse;Profile;Gaming;RGB;DPI;Warframe;GuildWars2;Heroic;Steam;
StartupNotify=true
StartupWMClass=io.github.thelion.G502ProfileManager
"""
    dest_desktop = desktop_dest_dir / "io.github.thelion.G502ProfileManager.desktop"
    dest_desktop.write_text(desktop_content, encoding="utf-8")
    dest_desktop.chmod(0o755)
    print(f"• Acceso directo instalado: {dest_desktop}")

    # Actualizar bases de datos del entorno de escritorio
    for cmd in [
        ["update-desktop-database", str(desktop_dest_dir)],
        ["kbuildsycoca6"],
        ["gtk-update-icon-cache", "-q", "-t", "-f", str(Path.home() / ".local/share/icons/hicolor")],
    ]:
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        except FileNotFoundError:
            pass

    print("\n✓ ¡Acceso directo instalado con éxito en el sistema!")
    print("  Ahora puedes buscar 'G502 Profile Manager' en el menú de KDE Plasma o KRunner.\n")


def cmd_uninstall_desktop(args):
    import subprocess

    desktop_file = Path.home() / ".local/share/applications/io.github.thelion.G502ProfileManager.desktop"
    icon_file = Path.home() / ".local/share/icons/hicolor/scalable/apps/io.github.thelion.G502ProfileManager.svg"

    removed = False
    if desktop_file.exists():
        desktop_file.unlink()
        print(f"• Eliminado: {desktop_file}")
        removed = True
    if icon_file.exists():
        icon_file.unlink()
        print(f"• Eliminado: {icon_file}")
        removed = True

    if removed:
        for cmd in [
            ["update-desktop-database", str(Path.home() / ".local/share/applications")],
            ["kbuildsycoca6"],
            ["gtk-update-icon-cache", "-q", "-t", "-f", str(Path.home() / ".local/share/icons/hicolor")],
        ]:
            try:
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            except FileNotFoundError:
                pass
        print("\n✓ Acceso directo desinstalado del sistema correctamente.\n")
    else:
        print("\nNo se encontró ninguna instalación previa del acceso directo.\n")


def main():
    parser = create_parser()
    args = parser.parse_args()

    handlers = {
        "list": cmd_list,
        "profiles": cmd_profiles,
        "create": cmd_create,
        "presets": cmd_presets,
        "catalog": cmd_presets,
        "add-action": cmd_add_action,
        "assign": cmd_assign,
        "reset": cmd_reset,
        "run": cmd_run,
        "engine": cmd_run,
        "gui": cmd_gui,
        "install-desktop": cmd_install_desktop,
        "uninstall-desktop": cmd_uninstall_desktop,
    }

    handler = handlers.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()