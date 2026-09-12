"""
Capa de adaptadores e integraciones para G502 Profile Manager.
"""

from .action_presets import (
    get_preset_actions_for_application,
    populate_application_actions,
)
from .application_discovery_adapter import ApplicationDiscoveryAdapter
from .ratbag_adapter import (
    G502_BUTTON_INDEX_MAP,
    RatbagDeviceAdapter,
    normalize_key_to_input_code,
)

__all__ = [
    "ApplicationDiscoveryAdapter",
    "G502_BUTTON_INDEX_MAP",
    "RatbagDeviceAdapter",
    "get_preset_actions_for_application",
    "normalize_key_to_input_code",
    "populate_application_actions",
]
