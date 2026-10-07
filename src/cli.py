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
    all_apps = discovery.discover_all_applications()

    print(f"Total aplicaciones detectadas: {len(all_apps)}\n")
    for app in all_apps:
        profiles = manager.get_profiles_for_application(app.application_id)
        has_preset = "✓ Presets disponibles" if catalog.has_catalog(app.application_id) else "—"
        print(f"• [{app.application_id}] {app.name}")
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
    repo, manager, *_ = get_services()
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
    import logging
    log_level = logging.DEBUG if getattr(args, "verbose", False) else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    repo, manager, discovery, adapter, catalog = get_services()
    engine = AutomationEngine(
        profile_manager=manager,
        device_adapter=adapter,
        discovery_adapter=discovery,
        catalog_service=catalog,
        check_interval=args.interval,
    )
    engine.run()


def cmd_export(args):
    _, manager, *_ = get_services()
    from datetime import datetime

    if args.file:
        dest_path = Path(args.file)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest_path = Path(f"g502-profiles-backup-{timestamp}.json")

    try:
        count = manager.export_to_file(dest_path, application_id=args.app)
        print(f"\n✓ Se exportaron exitosamente {count} perfil(es) a:")
        print(f"  {dest_path.resolve()}\n")
    except Exception as e:
        print(f"\nError al exportar perfiles: {e}\n")


def cmd_import(args):
    _, manager, *_ = get_services()
    src_path = Path(args.file)

    if not src_path.exists():
        print(f"\nError: El archivo '{src_path}' no existe.\n")
        return

    try:
        imported, skipped = manager.import_from_file(src_path, overwrite=args.overwrite)
        print(f"\n✓ Importación completada desde {src_path.resolve()}:")
        print(f"  • Perfiles importados/actualizados: {imported}")
        print(f"  • Perfiles omitidos:                {skipped}")
        if skipped > 0 and not args.overwrite:
            print("  (Consejo: Usa --overwrite si deseas reemplazar los perfiles existentes con el mismo ID)\n")
        else:
            print()
    except Exception as e:
        print(f"\nError al importar perfiles: {e}\n")


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
    run_p.add_argument("-v", "--verbose", action="store_true", help="Habilita registros detallados de depuración (DEBUG).")

    engine_p = subparsers.add_parser("engine", help="Alias para 'run'.")
    engine_p.add_argument("--interval", type=float, default=2.0, help="Intervalo de chequeo en segundos.")
    engine_p.add_argument("-v", "--verbose", action="store_true", help="Habilita registros detallados de depuración (DEBUG).")

    # gui
    subparsers.add_parser("status", help="Muestra el estado del hardware conectado y los perfiles.")
    subparsers.add_parser("gui", help="Inicia la interfaz gráfica nativa (GTK4 + Libadwaita).")

    # export / import portability
    export_p = subparsers.add_parser("export", help="Exporta perfiles a un archivo JSON para respaldo o migración.")
    export_p.add_argument("file", nargs="?", default=None, help="Ruta del archivo JSON de destino (opcional).")
    export_p.add_argument("--app", default=None, help="Filtrar por ID de aplicación (ej. steam:230410).")

    import_p = subparsers.add_parser("import", help="Importa perfiles desde un archivo JSON externo.")
    import_p.add_argument("file", help="Ruta al archivo JSON a importar.")
    import_p.add_argument("--overwrite", action="store_true", help="Sobrescribe perfiles existentes si sus IDs coinciden.")

    # desktop integration
    subparsers.add_parser("install-desktop", help="Instala el acceso directo y su icono en el menú de aplicaciones del sistema.")
    subparsers.add_parser("uninstall-desktop", help="Desinstala el acceso directo y su icono del sistema.")

    # systemd user service integration
    subparsers.add_parser("install-service", help="Instala y activa el demonio como servicio de usuario systemd (--user).")
    subparsers.add_parser("uninstall-service", help="Detiene y desinstala el servicio systemd del usuario.")
    # bin path integration
    subparsers.add_parser("install-bin", help="Instala los ejecutables 'g502' y 'g502-gui' en ~/.local/bin.")
    subparsers.add_parser("uninstall-bin", help="Desinstala los ejecutables 'g502' y 'g502-gui' de ~/.local/bin.")

    return parser


def cmd_status(args):
    repo, manager, discovery, adapter, _ = get_services()
    device = adapter.find_device()
    print("\n=========================================")
    print("      G502 Profile Manager - Estado      ")
    print("=========================================")
    if device:
        variant = adapter.detect_device_variant(device)
        bat = adapter.get_battery_level(device) if variant.capabilities.has_battery else None
        bat_str = f" | Batería: 🔋 {bat}%" if bat is not None else ""
        print(f"• Hardware:     {variant.name}")
        print(f"  ID libratbag: {device}{bat_str}")
        print(f"  Sensor máx:   {variant.capabilities.max_dpi:,} DPI")
        rgb_str = "RGB" if variant.capabilities.has_rgb else "Sin RGB"
        print(f"  Iluminación:  {variant.capabilities.led_zones} zona(s) ({rgb_str})")
        if variant.key != "g502_hero":
            print("  Soporte:      Experimental (reporta anomalías en: https://github.com/TheLioN25/g502-profile-manager/issues)")
    else:
        print("• Hardware:     Ningún ratón G502 detectado vía libratbag.")
    profiles = repo.list_all()
    print(f"• Repositorio:  {len(profiles)} perfil(es) registrado(s)")
    print("=========================================\n")


def cmd_gui(args):
    try:
        from gi.repository import GLib
        GLib.set_prgname("io.github.thelion.G502ProfileManager")
        GLib.set_application_name("G502 Profile Manager")
    except Exception:
        pass
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
    hicolor_root = Path.home() / ".local/share/icons/hicolor"
    icons_dest_dir = hicolor_root / "scalable/apps"

    desktop_dest_dir.mkdir(parents=True, exist_ok=True)
    icons_dest_dir.mkdir(parents=True, exist_ok=True)

    # 1. Asegurar archivo index.theme en ~/.local/share/icons/hicolor para que gtk-update-icon-cache no falle
    hicolor_theme_file = hicolor_root / "index.theme"
    if not hicolor_theme_file.exists():
        system_index = Path("/usr/share/icons/hicolor/index.theme")
        if system_index.exists():
            shutil.copy2(system_index, hicolor_theme_file)
        else:
            hicolor_theme_file.write_text(
                "[Icon Theme]\nName=Hicolor\nComment=Fallback icon theme\nHidden=true\nDirectories=scalable/apps,16x16/apps,22x22/apps,24x24/apps,32x32/apps,48x48/apps,64x64/apps,128x128/apps,256x256/apps,512x512/apps\n",
                encoding="utf-8",
            )

    # 2. Instalar icono SVG vectorial en scalable, ~/.local/share/icons y pixmaps
    src_icon = repo_root / "data" / "icons" / "io.github.thelion.G502ProfileManager.svg"
    dest_icon = icons_dest_dir / "io.github.thelion.G502ProfileManager.svg"
    if src_icon.exists():
        shutil.copy2(src_icon, dest_icon)
        # Copiar también a rutas estándar de fallback en el entorno de escritorio
        loose_icons = Path.home() / ".local/share/icons"
        pixmaps_dir = Path.home() / ".local/share/pixmaps"
        loose_icons.mkdir(parents=True, exist_ok=True)
        pixmaps_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_icon, loose_icons / "io.github.thelion.G502ProfileManager.svg")
        shutil.copy2(src_icon, pixmaps_dir / "io.github.thelion.G502ProfileManager.svg")
        print(f"• Icono SVG instalado: {dest_icon}")

    # 3. Instalar versiones rasterizadas PNG multi-resolución para barras de tareas (KDE Plasma, GNOME, XFCE)
    sizes = [16, 22, 24, 32, 48, 64, 128, 256, 512]
    for sz in sizes:
        png_src = repo_root / "data" / "icons" / f"io.github.thelion.G502ProfileManager_{sz}x{sz}.png"
        sz_dir = hicolor_root / f"{sz}x{sz}" / "apps"
        sz_dir.mkdir(parents=True, exist_ok=True)
        sz_dest = sz_dir / "io.github.thelion.G502ProfileManager.png"
        if png_src.exists():
            shutil.copy2(png_src, sz_dest)
        elif src_icon.exists():
            try:
                import cairo, gi
                gi.require_version("Rsvg", "2.0")
                from gi.repository import Rsvg
                handle = Rsvg.Handle.new_from_file(str(src_icon))
                surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, sz, sz)
                ctx = cairo.Context(surf)
                rect = Rsvg.Rectangle()
                rect.x, rect.y, rect.width, rect.height = 0, 0, sz, sz
                handle.render_document(ctx, rect)
                surf.write_to_png(str(sz_dest))
            except Exception:
                pass

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

    # Actualizar bases de datos del entorno de escritorio y caché de iconos
    for cmd in [
        ["update-desktop-database", str(desktop_dest_dir)],
        ["kbuildsycoca6", "--noincremental"],
        ["gtk-update-icon-cache", "-q", "-t", "-f", str(hicolor_root)],
    ]:
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        except FileNotFoundError:
            pass

    print("\n✓ ¡Acceso directo e iconos instalados con éxito en el sistema!")
    print("  Ahora puedes buscar 'G502 Profile Manager' en el menú de KDE Plasma o KRunner.\n")


def cmd_uninstall_desktop(args):
    import subprocess

    desktop_file = Path.home() / ".local/share/applications/io.github.thelion.G502ProfileManager.desktop"
    icon_file = Path.home() / ".local/share/icons/hicolor/scalable/apps/io.github.thelion.G502ProfileManager.svg"
    loose_icon = Path.home() / ".local/share/icons/io.github.thelion.G502ProfileManager.svg"
    pixmaps_icon = Path.home() / ".local/share/pixmaps/io.github.thelion.G502ProfileManager.svg"

    removed = False
    if desktop_file.exists():
        desktop_file.unlink()
        print(f"• Eliminado: {desktop_file}")
        removed = True
    if icon_file.exists():
        icon_file.unlink()
        print(f"• Eliminado: {icon_file}")
        removed = True
    if loose_icon.exists():
        loose_icon.unlink()
        removed = True
    if pixmaps_icon.exists():
        pixmaps_icon.unlink()
        removed = True

    # Eliminar iconos rasterizados PNG
    hicolor_root = Path.home() / ".local/share/icons/hicolor"
    sizes = [16, 22, 24, 32, 48, 64, 128, 256, 512]
    for sz in sizes:
        sz_icon = hicolor_root / f"{sz}x{sz}" / "apps" / "io.github.thelion.G502ProfileManager.png"
        if sz_icon.exists():
            sz_icon.unlink()
            removed = True

    # Actualizar cachés tras desinstalación
    for cmd in [
        ["update-desktop-database", str(Path.home() / ".local/share/applications")],
        ["kbuildsycoca6", "--noincremental"],
        ["gtk-update-icon-cache", "-q", "-t", "-f", str(hicolor_root)],
    ]:
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        except FileNotFoundError:
            pass

    if removed:
        print("\n✓ ¡Acceso directo e iconos desinstalados correctamente!\n")
    else:
        print("\nNo se encontraron accesos directos o iconos instalados.\n")


def cmd_install_service(args):
    import subprocess

    repo_root = Path(__file__).resolve().parent.parent
    systemd_user_dir = Path.home() / ".config/systemd/user"
    systemd_user_dir.mkdir(parents=True, exist_ok=True)

    service_content = f"""[Unit]
Description=G502 Profile Manager - Demonio de automatización en segundo plano
Documentation=https://github.com/TheLioN25/g502-profile-manager
After=default.target

[Service]
Type=simple
ExecStart={sys.executable} {repo_root / 'src/cli.py'} run
Restart=on-failure
RestartSec=5s
TimeoutStopSec=15s
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=default.target
"""
    service_file = systemd_user_dir / "g502-profile-manager.service"
    service_file.write_text(service_content, encoding="utf-8")
    print(f"• Archivo de servicio creado: {service_file}")

    # Recargar systemd y habilitar/arrancar servicio
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
    subprocess.run(["systemctl", "--user", "enable", "--now", "g502-profile-manager.service"], check=False)

    status_res = subprocess.run(
        ["systemctl", "--user", "is-active", "g502-profile-manager.service"],
        capture_output=True,
        text=True,
        check=False,
    )
    is_active = status_res.stdout.strip() == "active"

    if is_active:
        print("\n✓ ¡Servicio systemd --user instalado y ejecutándose exitosamente!")
    else:
        print(f"\n• Servicio instalado. Estado actual: {status_res.stdout.strip()}")

    print("  Comandos útiles:")
    print("  - Ver logs en vivo: journalctl --user -u g502-profile-manager.service -f")
    print("  - Ver estado:       systemctl --user status g502-profile-manager.service")
    print("  - Detener servicio: systemctl --user stop g502-profile-manager.service\n")


def cmd_uninstall_service(args):
    import subprocess

    service_file = Path.home() / ".config/systemd/user/g502-profile-manager.service"

    # Detener y deshabilitar
    subprocess.run(["systemctl", "--user", "stop", "g502-profile-manager.service"], check=False)
    subprocess.run(["systemctl", "--user", "disable", "g502-profile-manager.service"], check=False)

    removed = False
    if service_file.exists():
        service_file.unlink()
        print(f"• Eliminado: {service_file}")
        removed = True

    subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
    subprocess.run(["systemctl", "--user", "reset-failed"], check=False)

    if removed:
        print("\n✓ Servicio systemd --user desinstalado correctamente.\n")
    else:
        print("\nNo se encontró ningún archivo de servicio instalado.\n")


def cmd_service_status(args):
    import subprocess

    subprocess.run(["systemctl", "--user", "status", "g502-profile-manager.service"])


def cmd_install_bin(args):
    import subprocess
    repo_root = Path(__file__).resolve().parent.parent
    script = repo_root / "scripts" / "install-bin.sh"
    if script.exists():
        subprocess.run([str(script)], check=False)


def cmd_uninstall_bin(args):
    import subprocess
    repo_root = Path(__file__).resolve().parent.parent
    script = repo_root / "scripts" / "uninstall-bin.sh"
    if script.exists():
        subprocess.run([str(script)], check=False)


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
        "status": cmd_status,
        "gui": cmd_gui,
        "export": cmd_export,
        "import": cmd_import,
        "install-desktop": cmd_install_desktop,
        "uninstall-desktop": cmd_uninstall_desktop,
        "install-service": cmd_install_service,
        "uninstall-service": cmd_uninstall_service,
        "service-status": cmd_service_status,
        "install-bin": cmd_install_bin,
        "uninstall-bin": cmd_uninstall_bin,
    }

    handler = handlers.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()