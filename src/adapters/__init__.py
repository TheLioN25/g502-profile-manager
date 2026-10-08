"""
Capa de adaptadores e integraciones para G502 Profile Manager.
"""

from .action_presets import (
    get_preset_actions_for_application,
    populate_application_actions,
)
from .application_discovery_adapter import ApplicationDiscoveryAdapter
from .application_resolver import (
    ActiveApplication,
    build_desktop_entry_index,
    combine_active_applications,
    resolve_active_applications,
    resolve_steam_applications,
)
from .desktop_entries import (
    DESKTOP_DIRECTORIES,
    DesktopEntry,
    discover_desktop_entries,
    parse_desktop_entry,
)
from .epic_discovery import (
    EpicAppManifest,
    discover_active_epic_apps,
    discover_all_installed_epic_apps,
    discover_heroic_installed_apps,
    resolve_epic_applications,
)
from .process_discovery import (
    ProcessInfo,
    deduplicate_processes,
    discover_processes,
    extract_executable_name,
    get_effective_executable_path,
    process_name_is_running,
    search_processes,
)
from .ratbag_adapter import (
    G502_BUTTON_INDEX_MAP,
    RatbagDeviceAdapter,
    normalize_key_to_input_code,
)
from .steam_discovery import (
    ActiveSteamApplication,
    SteamAppManifest,
    discover_active_steam_apps,
    discover_installed_steam_apps,
    extract_steam_app_id,
)

__all__ = [
    "ActiveApplication",
    "ActiveSteamApplication",
    "ApplicationDiscoveryAdapter",
    "DESKTOP_DIRECTORIES",
    "DesktopEntry",
    "EpicAppManifest",
    "G502_BUTTON_INDEX_MAP",
    "ProcessInfo",
    "RatbagDeviceAdapter",
    "SteamAppManifest",
    "build_desktop_entry_index",
    "combine_active_applications",
    "deduplicate_processes",
    "discover_active_epic_apps",
    "discover_active_steam_apps",
    "discover_all_installed_epic_apps",
    "discover_desktop_entries",
    "discover_heroic_installed_apps",
    "discover_installed_steam_apps",
    "discover_processes",
    "extract_executable_name",
    "extract_steam_app_id",
    "get_effective_executable_path",
    "get_preset_actions_for_application",
    "normalize_key_to_input_code",
    "populate_application_actions",
    "process_name_is_running",
    "resolve_active_applications",
    "resolve_epic_applications",
    "resolve_steam_applications",
    "search_processes",
]
