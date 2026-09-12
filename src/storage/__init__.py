"""
Capa de almacenamiento y persistencia para G502 Profile Manager.
"""

from .profile_repository import JsonProfileRepository, ProfileRepository

__all__ = [
    "JsonProfileRepository",
    "ProfileRepository",
]
