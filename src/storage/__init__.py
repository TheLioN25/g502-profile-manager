"""
Capa de almacenamiento y persistencia para G502 Profile Manager.
"""

from .profile_repository import CorruptedProfileRepositoryError, JsonProfileRepository, ProfileRepository

__all__ = [
    "CorruptedProfileRepositoryError",
    "JsonProfileRepository",
    "ProfileRepository",
]
