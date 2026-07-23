#!/usr/bin/env python3

import argparse
from application_manager import (
    list_configurable_applications,
    get_configurable_application,
)


def list_applications(args):
    applications = list_configurable_applications()

    total = len(applications)
    configured = sum(
        application.configured
        for application in applications
    )

    print("Aplicaciones disponibles")
    print("========================")
    print(f"Total: {total}")
    print(f"Configuradas: {configured}")
    print()

    print_applications(applications)


def print_applications(applications):
    for application in applications:
        print_application(application)
        print()


def print_application(application):
    if application.configured:
        print_configured_application(application)
    else:
        print_unconfigured_application(application)


def print_configured_application(application):
    print(f"[X] {application.catalog_entry.name}")
    print(f"    Perfil: {application.profile}")
    print(f"    Prioridad: {application.priority}")


def print_unconfigured_application(application):
    print(f"[ ] {application.catalog_entry.name}")


def not_implemented(args):
    print(f"Comando '{args.command}' aún no implementado.")


def configure_application(args):
    if args.application is None:
        print("Modo interactivo aún no implementado.")
        return

    application = get_configurable_application(
        args.application,
    )

    if application is None:
        print(
            f"No se encontró ninguna aplicación llamada "
            f"'{args.application}'."
        )
        return

    print_selected_application(application)

    profile = request_profile()

    print(profile)


def request_profile():
    print()

    profile = input("Ingrese el perfil: ")

    return profile


def print_selected_application(application):
    print("Aplicación encontrada")
    print("=====================")
    print()

    print(f"Nombre: {application.catalog_entry.name}")
    print(f"Fuente: {application.catalog_entry.source}")

    if application.configured:
        print()
        print("Estado: Configurada")
        print(f"Perfil: {application.profile}")
        print(f"Prioridad: {application.priority}")
    else:
        print()
        print("Estado: No configurada")


def create_parser():
    parser = argparse.ArgumentParser(
        prog="g502-profile",
        description="Administrador de perfiles para Logitech G502 HERO.",
    )

    parser.add_argument(
        "--version",
        action="version",
        version="g502-profile 0.2.0-dev",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    commands = {
        "list": (
            "Lista todas las aplicaciones detectadas.",
            list_applications,
        ),
        "configured": (
            "Lista las aplicaciones configuradas.",
            not_implemented,
        ),
        "configure": (
            "Configura una aplicación.",
            configure_application,
        ),
        "update": (
            "Actualiza una configuración existente.",
            not_implemented,
        ),
        "remove": (
            "Elimina una configuración.",
            not_implemented,
        ),
        "engine": (
            "Inicia el motor automático.",
            not_implemented,
        ),
    }

    for name, (help_text, handler) in commands.items():
        command = subparsers.add_parser(
            name,
            help=help_text,
        )
        command.set_defaults(handler=handler)

        if name == "configure":
            command.add_argument(
                "application",
                nargs="?",
                help="Nombre de la aplicación a configurar.",
            )

    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()