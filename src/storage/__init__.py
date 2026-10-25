"""
Capa de almacenamiento y persistencia para G502 Profile Manager.
"""

from .profile_repository import (
    CorruptedProfileRepositoryError,
    DEFAULT_PROFILES_FILE,
    JsonProfileRepository,
    ProfileLockError,
    ProfileRepository,
)

__all__ = [
    "CorruptedProfileRepositoryError",
    "DEFAULT_PROFILES_FILE",
    "JsonProfileRepository",
    "ProfileLockError",
    "ProfileRepository",
]
