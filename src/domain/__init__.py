"""
Capa de Dominio de G502 Profile Manager.
"""

from .application import Action, Application
from .device import (
    Button,
    Device,
    DeviceCapabilities,
    DeviceVariant,
    G502_VARIANTS,
    DEFAULT_VARIANT,
    get_variant_by_key,
)
from .profile import Assignment, DpiConfiguration, Profile

__all__ = [
    "Action",
    "Application",
    "Assignment",
    "Button",
    "Device",
    "DeviceCapabilities",
    "DeviceVariant",
    "G502_VARIANTS",
    "DEFAULT_VARIANT",
    "get_variant_by_key",
    "DpiConfiguration",
    "Profile",
]
