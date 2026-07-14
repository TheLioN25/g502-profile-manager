#!/usr/bin/env python3

import json
from copy import deepcopy
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = PROJECT_DIR / "config.json"

REQUIRED_CONFIG_KEYS = {
    "device",
    "desktop_profile",
    "check_interval",
    "applications",
}

REQUIRED_APPLICATION_KEYS = {
    "name",
    "application_id",
    "source",
    "profile",
    "priority",
}


class ConfigError(Exception):
    """Error relacionado con la configuración."""


def validate_application(application):
    if not isinstance(application, dict):
        raise ConfigError("La aplicación debe ser un objeto.")

    missing = REQUIRED_APPLICATION_KEYS - application.keys()

    if missing:
        raise ConfigError(
            "Faltan campos obligatorios: "
            + ", ".join(sorted(missing))
        )

    if not isinstance(application["name"], str):
        raise ConfigError("'name' debe ser texto.")

    if not application["name"].strip():
        raise ConfigError("'name' no puede estar vacío.")

    if not isinstance(application["application_id"], str):
        raise ConfigError("'application_id' debe ser texto.")

    if not application["application_id"].strip():
        raise ConfigError("'application_id' no puede estar vacío.")

    if not isinstance(application["source"], str):
        raise ConfigError("'source' debe ser texto.")

    if not application["source"].strip():
        raise ConfigError("'source' no puede estar vacío.")

    if not isinstance(application["profile"], int):
        raise ConfigError("'profile' debe ser un número entero.")

    if not 0 <= application["profile"] <= 4:
        raise ConfigError("'profile' debe estar entre 0 y 4.")

    if not isinstance(application["priority"], int):
        raise ConfigError("'priority' debe ser un número entero.")


def validate_config(config):
    if not isinstance(config, dict):
        raise ConfigError("La configuración debe ser un objeto.")

    missing = REQUIRED_CONFIG_KEYS - config.keys()

    if missing:
        raise ConfigError(
            "Faltan campos obligatorios: "
            + ", ".join(sorted(missing))
        )

    if not isinstance(config["device"], str):
        raise ConfigError("'device' debe ser texto.")

    if not config["device"].strip():
        raise ConfigError("'device' no puede estar vacío.")

    if not isinstance(config["desktop_profile"], int):
        raise ConfigError("'desktop_profile' debe ser un número entero.")

    if not 0 <= config["desktop_profile"] <= 4:
        raise ConfigError("'desktop_profile' debe estar entre 0 y 4.")

    if not isinstance(config["check_interval"], (int, float)):
        raise ConfigError("'check_interval' debe ser numérico.")

    if config["check_interval"] <= 0:
        raise ConfigError("'check_interval' debe ser mayor que cero.")

    if not isinstance(config["applications"], list):
        raise ConfigError("'applications' debe ser una lista.")

    for application in config["applications"]:
        validate_application(application)


def load_config():
    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as file:
            config = json.load(file)
    except FileNotFoundError as error:
        raise ConfigError(
            f"No existe el archivo: {CONFIG_FILE}"
        ) from error
    except json.JSONDecodeError as error:
        raise ConfigError(
            f"JSON inválido: {error}"
        ) from error
    except OSError as error:
        raise ConfigError(
            f"No se pudo leer la configuración: {error}"
        ) from error

    validate_config(config)

    return config


def save_config(config):
    validate_config(config)

    temporary_file = CONFIG_FILE.with_suffix(".json.tmp")

    try:
        with temporary_file.open("w", encoding="utf-8") as file:
            json.dump(
                config,
                file,
                indent=4,
                ensure_ascii=False,
            )

            file.write("\n")

        temporary_file.replace(CONFIG_FILE)

    except OSError as error:
        raise ConfigError(
            f"No se pudo guardar la configuración: {error}"
        ) from error


def list_applications():
    config = load_config()
    return deepcopy(config["applications"])


def add_application(
    name,
    application_id,
    source,
    profile,
    priority,
):
    config = load_config()

    new_application = {
        "name": name.strip(),
        "application_id": application_id.strip(),
        "source": source.strip(),
        "profile": profile,
        "priority": priority,
    }

    validate_application(new_application)

    for application in config["applications"]:
        if application["name"].casefold() == new_application["name"].casefold():
            raise ConfigError(
                f"Ya existe una aplicación llamada '{new_application['name']}'."
            )

        if (
            application["source"].casefold()
            == new_application["source"].casefold()
            and application["application_id"].casefold()
            == new_application["application_id"].casefold()
        ):
            raise ConfigError(
                "La identidad de aplicación "
                f"'{new_application['source']} / "
                f"{new_application['application_id']}' ya está asociada."
            )

    config["applications"].append(new_application)
    save_config(config)


def remove_application(application_id, source):
    config = load_config()

    original_length = len(config["applications"])

    config["applications"] = [
        application
        for application in config["applications"]
        if not (
            application["source"].casefold() == source.casefold()
            and application["application_id"].casefold()
            == application_id.casefold()
        )
    ]

    if len(config["applications"]) == original_length:
        raise ConfigError(
            "No existe la identidad de aplicación "
            f"'{source} / {application_id}'."
        )

    save_config(config)


def update_application(
    current_name,
    new_name,
    new_application_id,
    new_source,
    new_profile,
    new_priority,
):
    config = load_config()

    updated_application = {
        "name": new_name.strip(),
        "application_id": new_application_id.strip(),
        "source": new_source.strip(),
        "profile": new_profile,
        "priority": new_priority,
    }

    validate_application(updated_application)

    target_application = None

    for application in config["applications"]:
        if application["name"].casefold() == current_name.casefold():
            target_application = application
            break

    if target_application is None:
        raise ConfigError(
            f"No existe la aplicación '{current_name}'."
        )

    for application in config["applications"]:
        if application is target_application:
            continue

        if (
            application["name"].casefold()
            == updated_application["name"].casefold()
        ):
            raise ConfigError(
                f"Ya existe una aplicación llamada "
                f"'{updated_application['name']}'."
            )

        if (
            application["source"].casefold()
            == updated_application["source"].casefold()
            and application["application_id"].casefold()
            == updated_application["application_id"].casefold()
        ):
            raise ConfigError(
                "La identidad de aplicación "
                f"'{updated_application['source']} / "
                f"{updated_application['application_id']}' ya está asociada."
            )

    target_application.update(updated_application)

    save_config(config)
