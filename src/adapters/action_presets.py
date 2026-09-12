"""
Módulo de catálogo de presets de acciones para juegos y aplicaciones.

Proporciona bibliotecas de acciones preconfiguradas con sus teclas y bindings
reales para juegos populares y contextos de productividad.
"""

from __future__ import annotations

from domain import Action, Application


PRESETS: dict[str, list[dict[str, str]]] = {
    # Warframe (Steam AppID 230410)
    "steam:230410": [
        {
            "action_id": "wf_ability_1",
            "name": "Habilidad 1",
            "description": "Lanza la primera habilidad del Warframe",
            "binding_type": "key",
            "binding_value": "1",
        },
        {
            "action_id": "wf_ability_2",
            "name": "Habilidad 2",
            "description": "Lanza la segunda habilidad del Warframe",
            "binding_type": "key",
            "binding_value": "2",
        },
        {
            "action_id": "wf_ability_3",
            "name": "Habilidad 3",
            "description": "Lanza la tercera habilidad del Warframe",
            "binding_type": "key",
            "binding_value": "3",
        },
        {
            "action_id": "wf_ability_4",
            "name": "Habilidad 4 (Ultimate)",
            "description": "Lanza la habilidad definitiva",
            "binding_type": "key",
            "binding_value": "4",
        },
        {
            "action_id": "wf_melee",
            "name": "Ataque Cuerpo a Cuerpo",
            "description": "Ataque cuerpo a cuerpo rápido",
            "binding_type": "key",
            "binding_value": "e",
        },
        {
            "action_id": "wf_crouch",
            "name": "Agacharse / Deslizarse",
            "description": "Agacharse o iniciar deslizamiento",
            "binding_type": "key",
            "binding_value": "leftctrl",
        },
        {
            "action_id": "wf_interact",
            "name": "Contextual / Interactuar",
            "description": "Abrir puertas, hackear o interactuar",
            "binding_type": "key",
            "binding_value": "x",
        },
    ],
    # Guild Wars 2 (Steam AppID 1284210)
    "steam:1284210": [
        {
            "action_id": "gw2_skill_1",
            "name": "Habilidad 1 (Auto-attack)",
            "description": "Primera habilidad de arma",
            "binding_type": "key",
            "binding_value": "1",
        },
        {
            "action_id": "gw2_skill_2",
            "name": "Habilidad 2",
            "description": "Segunda habilidad de arma",
            "binding_type": "key",
            "binding_value": "2",
        },
        {
            "action_id": "gw2_skill_3",
            "name": "Habilidad 3",
            "description": "Tercera habilidad de arma",
            "binding_type": "key",
            "binding_value": "3",
        },
        {
            "action_id": "gw2_dodge",
            "name": "Esquivar (Dodge)",
            "description": "Rodar evasivo",
            "binding_type": "key",
            "binding_value": "v",
        },
        {
            "action_id": "gw2_heal",
            "name": "Curación",
            "description": "Habilidad de curación de emergencia (Slot 6)",
            "binding_type": "key",
            "binding_value": "6",
        },
        {
            "action_id": "gw2_elite",
            "name": "Habilidad de Élite",
            "description": "Habilidad de élite (Slot 0)",
            "binding_type": "key",
            "binding_value": "0",
        },
    ],
    # Escritorio / General / Productividad
    "desktop:general": [
        {
            "action_id": "gen_copy",
            "name": "Copiar",
            "description": "Copiar al portapapeles (Ctrl+C)",
            "binding_type": "macro",
            "binding_value": "ctrl+c",
        },
        {
            "action_id": "gen_paste",
            "name": "Pegar",
            "description": "Pegar desde el portapapeles (Ctrl+V)",
            "binding_type": "macro",
            "binding_value": "ctrl+v",
        },
        {
            "action_id": "gen_undo",
            "name": "Deshacer",
            "description": "Deshacer última acción (Ctrl+Z)",
            "binding_type": "macro",
            "binding_value": "ctrl+z",
        },
    ],
}


from services.action_catalog import ActionCatalogService

_catalog_service = ActionCatalogService()


def get_preset_actions_for_application(application_id: str) -> tuple[Action, ...]:
    """
    Devuelve las acciones predefinidas disponibles para una aplicación.
    Consulta el servicio de catálogos y presets JSON modulares.
    """
    if not isinstance(application_id, str):
        return ()

    actions = _catalog_service.get_actions_for_application(application_id)
    if actions:
        return actions

    app_key = application_id.strip().casefold()
    raw_actions = PRESETS.get(app_key, [])

    result = []
    for item in raw_actions:
        result.append(
            Action(
                action_id=item["action_id"],
                name=item["name"],
                application_id=application_id.strip(),
                description=item.get("description", ""),
                binding_type=item.get("binding_type", "key"),
                binding_value=item.get("binding_value", ""),
                category=item.get("category", "General"),
            )
        )

    return tuple(result)


def populate_application_actions(application: Application) -> int:
    """
    Rellena una instancia de Application con las acciones predefinidas que le correspondan.
    Devuelve el número de acciones añadidas.
    """
    if not isinstance(application, Application):
        raise TypeError("application debe ser una instancia de Application.")

    return _catalog_service.populate_application_actions(application)
