#!/usr/bin/env python3

import argparse
from application_manager import list_configurable_applications


def list_applications(args):
    applications = list_configurable_applications()

    print_applications(applications)


def print_applications(applications):
    for application in applications:
        print_application(application)


def print_application(application):
    if application.configured:
        print_configured_application(application)
    else:
        print_unconfigured_application(application)


def print_configured_application(application):
    print(application)


def print_unconfigured_application(application):
    print(application)


def not_implemented(args):
    print(f"Comando '{args.command}' aún no implementado.")


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
            not_implemented,
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

    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
