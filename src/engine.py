#!/usr/bin/env python3

import subprocess
import time

from config_manager import ConfigError, load_config
from process_discovery import process_name_is_running

def run_command(command):
    """Ejecuta un comando del sistema y devuelve el resultado."""
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )


def mouse_available(device):
    """Comprueba que el dispositivo esté disponible mediante ratbagctl."""
    result = run_command(["ratbagctl", "list"])

    return (
        result.returncode == 0
        and device in result.stdout
    )


def get_active_profile(device):
    """Obtiene el perfil activo del mouse."""
    result = run_command(
        [
            "ratbagctl",
            device,
            "profile",
            "active",
            "get",
        ]
    )

    if result.returncode != 0:
        return None

    try:
        return int(result.stdout.strip())
    except ValueError:
        return None


def set_profile(device, profile):
    """
    Cambia el perfil únicamente cuando el perfil solicitado
    es diferente del perfil actualmente activo.
    """

    current_profile = get_active_profile(device)

    if current_profile == profile:
        return True

    result = run_command(
        [
            "ratbagctl",
            device,
            "profile",
            "active",
            "set",
            str(profile),
        ]
    )

    return result.returncode == 0


def find_active_application(applications):
    """
    Devuelve la aplicación ejecutándose con mayor prioridad.
    """

    running_applications = []

    for application in applications:

        if process_name_is_running(application["process"]):
            running_applications.append(application)

    if not running_applications:
        return None

    return max(
        running_applications,
        key=lambda application: application["priority"],
    )


def main():
    print("G502 Profile Manager - Engine")
    print("-----------------------------")

    try:
        config = load_config()

    except ConfigError as error:
        print(f"ERROR DE CONFIGURACIÓN: {error}")
        return

    device = config["device"]
    desktop_profile = config["desktop_profile"]
    check_interval = config["check_interval"]
    applications = config["applications"]

    print("Configuración cargada correctamente.")
    print(f"Aplicaciones configuradas: {len(applications)}")

    if not mouse_available(device):
        print(f"ERROR: Dispositivo no detectado: {device}")
        return

    print("Mouse detectado correctamente.")
    print(f"Perfil predeterminado: {desktop_profile}")
    print("Motor iniciado.")
    print("Presiona Ctrl+C para detenerlo.\n")

    last_mode = None

    try:

        while True:

            application = find_active_application(applications)

            if application:

                mode = application["name"]
                target_profile = application["profile"]

            else:

                mode = "Desktop"
                target_profile = desktop_profile

            if mode != last_mode:

                print(f"Aplicación activa: {mode}")
                print(f"Solicitando perfil: {target_profile}")

                if set_profile(device, target_profile):

                    print(
                        f"Perfil {target_profile} "
                        "activado correctamente.\n"
                    )

                else:

                    print(
                        "ERROR: No se pudo cambiar el perfil.\n"
                    )

                last_mode = mode

            time.sleep(check_interval)

    except KeyboardInterrupt:

        print("\nDeteniendo motor...")

        if set_profile(device, desktop_profile):

            print(
                f"Perfil {desktop_profile} restaurado."
            )

        else:

            print(
                "ADVERTENCIA: No se pudo restaurar "
                "el perfil predeterminado."
            )

        print("Motor detenido.")


if __name__ == "__main__":
    main()
