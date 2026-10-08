"""
Motor de automatización en tiempo real para G502 Profile Manager.

Supervisa los procesos del sistema, detecta lanzamientos de videojuegos y aplicaciones,
y aplica automáticamente las preferencias de interacción al ratón Logitech G502 HERO
utilizando la capa de dominio y adaptadores de hardware.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import threading
import time
from typing import Callable

logger_engine = logging.getLogger("g502.engine")

from adapters import (
    DESKTOP_DIRECTORIES,
    ApplicationDiscoveryAdapter,
    RatbagDeviceAdapter,
    combine_active_applications,
    discover_active_epic_apps,
    discover_active_steam_apps,
    discover_desktop_entries,
    discover_processes,
    parse_desktop_entry,
    resolve_active_applications,
    resolve_epic_applications,
    resolve_steam_applications,
)
from domain import DEFAULT_VARIANT, DeviceVariant, Profile
from services import ActionCatalogService, ProfileManager
from storage import JsonProfileRepository


DEFAULT_STEAM_LIBRARYFOLDERS_FILE = (
    Path.home() / ".local/share/Steam/steamapps/libraryfolders.vdf"
)
DEFAULT_PROFILES_FILE = Path.home() / ".config/g502-profiles.json"


class AutomationEngine:
    """
    Motor reactivo que supervisa los procesos del sistema y conmutadores de perfiles.
    Soporta Steam, Epic Games y aplicaciones de escritorio de Linux.
    """

    def __init__(
        self,
        profile_manager: ProfileManager,
        device_adapter: RatbagDeviceAdapter,
        check_interval: float = 2.0,
        steam_libraryfolders_file: Path | str = DEFAULT_STEAM_LIBRARYFOLDERS_FILE,
        target_device_name: str = "Logitech G502 HERO Gaming Mouse",
        desktop_profile_slot: int = 0,
        catalog_service: ActionCatalogService | None = None,
        discovery_adapter: ApplicationDiscoveryAdapter | None = None,
        logger: Callable[[str], None] | None = None,
        on_profile_applied: Callable[[str, Profile], None] | None = None,
        on_desktop_restored: Callable[[], None] | None = None,
    ):
        self._profile_manager = profile_manager
        self._device_adapter = device_adapter
        self._check_interval = check_interval
        self._steam_file = Path(steam_libraryfolders_file).expanduser().resolve()
        self._target_device_name = target_device_name
        self._desktop_profile_slot = desktop_profile_slot
        self._catalog_service = catalog_service or ActionCatalogService()
        self._discovery = discovery_adapter or ApplicationDiscoveryAdapter(steam_libraryfolders_file=self._steam_file)
        self._log = logger if logger is not None else logger_engine.info
        self._on_profile_applied = on_profile_applied
        self._on_desktop_restored = on_desktop_restored
        self._stop_event = threading.Event()

        self._device_id: str | None = None
        self._device_variant: DeviceVariant = DEFAULT_VARIANT
        self._battery_level: int | None = None
        self._current_profile_id: str | None = None
        self._current_profile_updated_at: str | None = None
        self._desktop_entries_cache = None
        self._tick_counter: int = 0

    @property
    def current_profile_id(self) -> str | None:
        """ID del perfil de dominio actualmente aplicado al mouse, o None si está en escritorio."""
        return self._current_profile_id

    @property
    def device_variant(self) -> DeviceVariant:
        """Variante de hardware de la familia G502 actualmente detectada."""
        return self._device_variant

    @property
    def battery_level(self) -> int | None:
        """Nivel de batería actual en porcentaje (0..100) o None si no aplica."""
        return self._battery_level

    def initialize(self) -> bool:
        """
        Verifica la conexión con el hardware del ratón, sincroniza catálogos
        con las descargas instaladas y cachea las entradas de escritorio.
        """
        # Si target_device_name es el genérico por defecto, buscar dinámicamente cualquier variante
        if self._target_device_name == "Logitech G502 HERO Gaming Mouse":
            self._device_id = self._device_adapter.find_device()
        else:
            self._device_id = self._device_adapter.find_device(self._target_device_name)

        if not self._device_id:
            self._log(f"Error: Dispositivo '{self._target_device_name}' no encontrado con ratbagctl.")
            return False

        if hasattr(self._device_adapter, "detect_device_variant"):
            self._device_variant = self._device_adapter.detect_device_variant(self._device_id)
        else:
            self._device_variant = DEFAULT_VARIANT

        if self._device_variant.capabilities.has_battery and hasattr(self._device_adapter, "get_cached_battery_level"):
            self._battery_level = self._device_adapter.get_cached_battery_level(self._device_id, ttl_seconds=30.0)

        bat_str = f" [Batería: 🔋 {self._battery_level}%]" if self._battery_level is not None else ""
        self._log(f"Dispositivo detectado: '{self._device_variant.name}' (libratbag ID: {self._device_id}){bat_str}")

        # Cachear entradas de escritorio
        self._desktop_entries_cache = [
            entry
            for desktop_file in discover_desktop_entries()
            if (entry := parse_desktop_entry(desktop_file)) is not None
        ]

        # Sincronizar catálogo con aplicaciones instaladas (Steam y Epic Games)
        self._sync_catalogs_with_installed()

        return True

    def _sync_catalogs_with_installed(self) -> None:
        """Comprueba e inicializa al vuelo los catálogos para juegos descargados."""
        all_apps = self._discovery.discover_all_applications()
        new_catalogs = self._catalog_service.sync_with_installed_applications(all_apps)
        for app_id in new_catalogs:
            self._log(f"[CATÁLOGO] ¡Nuevo juego detectado e instalado! Catálogo generado al vuelo para '{app_id}'.")

    def step(self) -> bool:
        """
        Ciclo de inspección y reacción:
        1. Comprueba si hay nuevas aplicaciones/juegos descargados periódicamente.
        2. Detecta procesos activos (Steam, Epic Games, Desktop).
        3. Aplica o restaura el perfil adecuado en el mouse G502 HERO.
        Devuelve True si la iteración se completó con éxito.
        """
        if not self._device_id:
            if self._target_device_name == "Logitech G502 HERO Gaming Mouse":
                self._device_id = self._device_adapter.find_device()
            else:
                self._device_id = self._device_adapter.find_device(self._target_device_name)
            if not self._device_id:
                return False
            if hasattr(self._device_adapter, "detect_device_variant"):
                self._device_variant = self._device_adapter.detect_device_variant(self._device_id)
            else:
                self._device_variant = DEFAULT_VARIANT

        if self._device_variant.capabilities.has_battery and hasattr(self._device_adapter, "get_cached_battery_level"):
            self._battery_level = self._device_adapter.get_cached_battery_level(self._device_id, ttl_seconds=30.0)

        # Cada 15 ciclos (~30s), revisar si se terminó de descargar un juego nuevo
        self._tick_counter += 1
        if self._tick_counter % 15 == 0:
            self._sync_catalogs_with_installed()

        processes = discover_processes()

        # 1. Resolver aplicaciones de escritorio
        desktop_apps = resolve_active_applications(
            processes,
            self._desktop_entries_cache or [],
        )

        # 2. Resolver juegos de Steam
        steam_active = discover_active_steam_apps(processes, self._steam_file)
        steam_apps = resolve_steam_applications(steam_active)

        # 3. Resolver juegos de Epic Games
        epic_active = discover_active_epic_apps(processes)
        epic_apps = resolve_epic_applications(epic_active)

        # 4. Combinar identidades activas
        active_applications = combine_active_applications((desktop_apps, steam_apps, epic_apps))

        # 5. Buscar si alguna aplicación activa tiene un perfil configurado
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
            current_slot = self._device_adapter.get_active_profile_slot(self._device_id)
            hardware_drifted = (current_slot is not None and current_slot != 0)

            needs_apply = (
                self._current_profile_id != target_profile.id
                or self._current_profile_updated_at != target_profile.updated_at
                or hardware_drifted
            )
            if needs_apply:
                self._log(f"\n[ACTIVO] Detectado: {detected_app_name} ({target_profile.application_id})")
                self._log(f"         Aplicando perfil: '{target_profile.name}' | DPI: {target_profile.dpi.dpi} | LED: {target_profile.led_color or 'N/A'}")

                success = self._device_adapter.apply_profile(self._device_id, target_profile)
                if success:
                    self._log("         Perfil aplicado al ratón con éxito.")
                    self._current_profile_id = target_profile.id
                    self._current_profile_updated_at = target_profile.updated_at
                    if self._on_profile_applied:
                        self._on_profile_applied(detected_app_name, target_profile)
                else:
                    self._log("         ADVERTENCIA: No se pudo aplicar el perfil completamente.")
        else:
            # Volver a perfil de escritorio si estábamos en otro perfil
            if self._current_profile_id is not None:
                self._log("\n[DESK] Volviendo al modo escritorio...")
                self.restore_desktop()

        return True

    def stop(self) -> None:
        """Detiene el bucle de monitoreo y restaura el perfil de escritorio."""
        self._stop_event.set()
        self.restore_desktop()
        self._log("Motor detenido limpiamente.")

    def run(self) -> None:
        """
        Bucle de monitoreo continuo.
        """
        if not self.initialize():
            return

        self._stop_event.clear()
        self._log(f"Motor iniciado con intervalo de {self._check_interval}s.")
        self._log("Presiona Ctrl+C o invoca stop() para detener y restaurar el perfil de escritorio.\n")

        try:
            import signal
            if threading.current_thread() is threading.main_thread():
                signal.signal(signal.SIGTERM, lambda *_: self._stop_event.set())
        except (ValueError, AttributeError):
            pass

        try:
            while not self._stop_event.is_set():
                try:
                    self.step()
                except Exception as ex:
                    self._log(f"Advertencia en ciclo de supervisión: {ex}")
                if self._stop_event.wait(timeout=self._check_interval):
                    break

        except KeyboardInterrupt:
            self._log("\nDeteniendo motor...")
        finally:
            self.stop()

    def restore_desktop(self) -> None:
        """Restaura el perfil de escritorio en el hardware del ratón."""
        if self._device_id:
            desktop_prof = self._profile_manager.get_active_profile_for_application("desktop:general")
            if desktop_prof is not None:
                self._device_adapter.apply_profile(self._device_id, desktop_prof)
                self._log("       Perfil de escritorio ('desktop:general') restaurado.")
            else:
                self._device_adapter.switch_profile_slot(self._device_id, self._desktop_profile_slot)
                self._log(f"       Perfil de escritorio (slot {self._desktop_profile_slot}) restaurado.")
            self._current_profile_id = None
            self._current_profile_updated_at = None
            if self._on_desktop_restored:
                self._on_desktop_restored()


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
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
