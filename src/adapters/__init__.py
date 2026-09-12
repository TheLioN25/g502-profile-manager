"""
Capa de adaptadores e integraciones para G502 Profile Manager.
"""

from .action_presets import (
    get_preset_actions_for_application,
    populate_application_actions,
)
from .application_discovery_adapter import ApplicationDiscoveryAdapter
from epic_discovery import (
    EpicAppManifest,
    discover_active_epic_apps,
    discover_all_installed_epic_apps,
    resolve_epic_applications,
)
from .ratbag_adapter import (
    G502_BUTTON_INDEX_MAP,
    RatbagDeviceAdapter,
    normalize_key_to_input_code,
)

__all__ = [
    "ApplicationDiscoveryAdapter",
    "EpicAppManifest",
    "G502_BUTTON_INDEX_MAP",
    "RatbagDeviceAdapter",
    "discover_active_epic_apps",
    "discover_all_installed_epic_apps",
    "get_preset_actions_for_application",
    "normalize_key_to_input_code",
    "populate_application_actions",
    "resolve_epic_applications",
]
