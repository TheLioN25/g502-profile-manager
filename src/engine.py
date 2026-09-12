"""
Motor de automatización en tiempo real para G502 Profile Manager.

Supervisa los procesos del sistema, detecta lanzamientos de videojuegos y aplicaciones,
y aplica automáticamente las preferencias de interacción al ratón Logitech G502 HERO
utilizando la capa de dominio y adaptadores de hardware.
"""

from __future__ import annotations

import os
from pathlib import Path
import time
from typing import Callable

from adapters import (
    ApplicationDiscoveryAdapter,
    RatbagDeviceAdapter,
)
from application_resolver import (
    combine_active_applications,
    resolve_active_applications,
    resolve_steam_applications,
)
from desktop_entries import (
    DESKTOP_DIRECTORIES,
    discover_desktop_entries,
    parse_desktop_entry,
)
from domain import Profile
from process_discovery import discover_processes
from services import ProfileManager
from steam_discovery import (
    discover_active_steam_apps,
)
from storage import JsonProfileRepository


DEFAULT_STEAM_LIBRARYFOLDERS_FILE = (
    Path.home() / ".local/share/Steam/steamapps/libraryfolders.vdf"
)
DEFAULT_PROFILES_FILE = Path.home() / ".config/g502-profiles.json"


class AutomationEngine:
    """
    Orquestador en tiempo real que reacciona a los cambios de aplicaciones activas.
    """

    def __init__(
        self,
        profile_manager: ProfileManager,
        device_adapter: RatbagDeviceAdapter,
        check_interval: float = 2.0,
        steam_libraryfolders_file: Path | str = DEFAULT_STEAM_LIBRARYFOLDERS_FILE,
        target_device_name: str = "Logitech G502 HERO Gaming Mouse",
        desktop_profile_slot: int = 0,
        logger: Callable[[str], None] = print,
    ):
        self._profile_manager = profile_manager
        self._device_adapter = device_adapter
        self._check_interval = check_interval
        self._steam_file = Path(steam_libraryfolders_file).expanduser().resolve()
        self._target_device_name = target_device_name
        self._desktop_profile_slot = desktop_profile_slot
        self._log = logger

        self._device_id: str | None = None
        self._current_profile_id: str | None = None
        self._desktop_entries_cache = None

    @property
    def current_profile_id(self) -> str | None:
        """ID del perfil de dominio actualmente aplicado al mouse, o None si está en escritorio."""
        return self._current_profile_id

    def initialize(self) -> bool:
        """
        Verifica la conexión con el hardware del ratón y cachea las entradas de escritorio.
        """
        self._device_id = self._device_adapter.find_device(self._target_device_name)
        if not self._device_id:
            self._log(f"ERROR: No se detectó el dispositivo '{self._target_device_name}'.")
            return False

        self._log(f"Mouse detectado: {self._device_id} ({self._target_device_name})")

        # Cachear entradas desktop para evitar lecturas masivas de disco en cada tick
        self._desktop_entries_cache = [
            entry
            for desktop_file in discover_desktop_entries()
            if (entry := parse_desktop_entry(desktop_file)) is not None
        ]

        return True

    def step(self) -> bool:
        """
        Ejecuta una iteración de detección y conmutación.
        Devuelve True si la iteración se completó con éxito.
        """
        if not self._device_id:
            return False

        processes = discover_processes()

        # 1. Resolver aplicaciones de escritorio
        desktop_apps = resolve_active_applications(
            processes,
            self._desktop_entries_cache or [],
        )

        # 2. Resolver juegos de Steam
        steam_active = discover_active_steam_apps(processes, self._steam_file)
        steam_apps = resolve_steam_applications(steam_active)

        # 3. Combinar identidades activas
        active_applications = combine_active_applications((desktop_apps, steam_apps))

        # 4. Buscar si alguna aplicación activa tiene un perfil configurado
        target_profile: Profile | None = None
        detected_app_name: str = "Escritorio"

        for app in active_applications:
            prof = self._profile_manager.get_active_profile_for_application(app.application_id)
            if prof is not None:
                target_profile = prof
                detected_app_name = app.name
                break

        # 5. Aplicar o restaurar según corresponda
        if target_profile is not None:
            if self._current_profile_id != target_profile.id:
                self._log(f"\n[ACTIVO] Detectado: {detected_app_name} ({target_profile.application_id})")
                self._log(f"         Aplicando perfil: '{target_profile.name}' | DPI: {target_profile.dpi.dpi} | LED: {target_profile.led_color or 'N/A'}")

                success = self._device_adapter.apply_profile(self._device_id, target_profile)
                if success:
                    self._log("         Perfil aplicado al ratón con éxito.")
                    self._current_profile_id = target_profile.id
                else:
                    self._log("         ADVERTENCIA: No se pudo aplicar el perfil completamente.")
        else:
            # Volver a perfil de escritorio si estábamos en otro perfil
            if self._current_profile_id is not None:
                self._log(f"\n[DESK] Volviendo al modo escritorio...")
                self._device_adapter.switch_profile_slot(self._device_id, self._desktop_profile_slot)
                self._current_profile_id = None
                self._log(f"       Perfil de escritorio (slot {self._desktop_profile_slot}) restaurado.")

        return True

    def run(self) -> None:
        """
        Bucle de monitoreo continuo.
        """
        if not self.initialize():
            return

        self._log(f"Motor iniciado con intervalo de {self._check_interval}s.")
        self._log("Presiona Ctrl+C para detener y restaurar el perfil de escritorio.\n")

        try:
            while True:
                self.step()
                time.sleep(self._check_interval)

        except KeyboardInterrupt:
            self._log("\nDeteniendo motor...")
            self.restore_desktop()
            self._log("Motor detenido limpiamente.")

    def restore_desktop(self) -> None:
        """Restaura la ranura de hardware predeterminada del escritorio."""
        if self._device_id:
            self._device_adapter.switch_profile_slot(self._device_id, self._desktop_profile_slot)
            self._current_profile_id = None


def main():
    repo = JsonProfileRepository(DEFAULT_PROFILES_FILE)
    manager = ProfileManager(repo)
    adapter = RatbagDeviceAdapter()

    engine = AutomationEngine(
        profile_manager=manager,
        device_adapter=adapter,
        check_interval=2.0,
    )
    engine.run()


if __name__ == "__main__":
    main()
