#!/usr/bin/env python3

import argparse


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
        "list": "Lista todas las aplicaciones detectadas.",
        "configured": "Lista las aplicaciones configuradas.",
        "configure": "Configura una aplicación.",
        "update": "Actualiza una configuración existente.",
        "remove": "Elimina una configuración.",
        "engine": "Inicia el motor automático.",
    }

    for name, help_text in commands.items():
        command = subparsers.add_parser(
            name,
            help=help_text,
        )
        command.set_defaults(handler=not_implemented)

    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
