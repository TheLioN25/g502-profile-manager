"""
Capa de almacenamiento y persistencia para G502 Profile Manager.
"""

from .profile_repository import (
    CorruptedProfileRepositoryError,
    JsonProfileRepository,
    ProfileLockError,
    ProfileRepository,
    get_default_profiles_file,
)

__all__ = [
    "CorruptedProfileRepositoryError",
    "JsonProfileRepository",
    "ProfileLockError",
    "ProfileRepository",
    "get_default_profiles_file",
]
