"""
Adaptador de notificaciones de escritorio y OSD para G502 Profile Manager.

Proporciona notificaciones discretas mediante D-Bus nativo (org.freedesktop.Notifications)
y fallback a notify-send para informar al usuario de cambios de perfil en pantalla completa.
"""

from __future__ import annotations

import logging
import subprocess
import time
from typing import Callable

logger = logging.getLogger("g502.notifications")

from i18n import _


class DesktopNotificationAdapter:
    """
    Adaptador para el despacho de notificaciones OSD al conmutar perfiles.
    Utiliza Gio.DBusConnection directamente para rendimiento de microsegundos,
    con fallback a notify-send en caso de ser necesario.
    """

    def __init__(
        self,
        enabled: bool = True,
        app_name: str = "G502 Profile Manager",
        icon: str = "io.github.thelion.G502ProfileManager",
        dbus_call_sync: Callable[..., tuple] | None = None,
        command_runner: Callable[..., subprocess.CompletedProcess] | None = None,
        debounce_window_sec: float = 3.0,
        max_burst_count: int = 3,
        burst_window_sec: float = 10.0,
        circuit_cooldown_sec: float = 15.0,
    ):
        self._enabled = enabled
        self._app_name = app_name
        self._icon = icon
        self._custom_dbus_call = dbus_call_sync
        self._runner = command_runner or subprocess.run
        self._dbus_conn = None
        self._dbus_init_attempted = False
        self._dbus_last_attempt = 0.0
        self._dbus_retry_cooldown_sec = 30.0
        self._debounce_window_sec = debounce_window_sec
        self._last_notification_key: tuple[str, str] | None = None
        self._last_notification_time: float = 0.0

        # Parámetros del Cortacircuitos (Circuit Breaker)
        self._max_burst_count = max_burst_count
        self._burst_window_sec = burst_window_sec
        self._circuit_cooldown_sec = circuit_cooldown_sec
        self._notification_timestamps: list[float] = []
        self._circuit_open_until: float = 0.0

    @property
    def enabled(self) -> bool:
        """Determina si las notificaciones OSD están habilitadas."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = bool(value)

    def _get_dbus_connection(self):
        """Devuelve la conexión al bus de sesión, reintentando tras un fallo transitorio."""
        if self._dbus_conn is not None:
            return self._dbus_conn
        now = time.monotonic()
        if self._dbus_init_attempted and (now - self._dbus_last_attempt) < self._dbus_retry_cooldown_sec:
            return None
        self._dbus_last_attempt = now
        try:
            from gi.repository import Gio
            self._dbus_conn = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            self._dbus_init_attempted = True
        except Exception as e:
            logger.debug("No se pudo obtener conexión Gio D-Bus para notificaciones: %s", e)
            self._dbus_conn = None
        return self._dbus_conn

    def send_notification(
        self,
        title: str,
        body: str,
        icon: str | None = None,
        timeout_ms: int = 1800,
        synchronous_id: str = "g502-profile-change",
        force: bool = False,
    ) -> bool:
        """
        Envía una notificación discreta de escritorio.
        Configura hints transitorios para no interferir con juegos a pantalla completa.
        Incluye protección debounce y cortacircuitos (circuit breaker) anti-ráfaga.
        """
        if not self._enabled:
            return False

        now = time.monotonic()

        # 1. Cortacircuitos (Circuit Breaker): supresión si el circuito está abierto
        if not force and now < self._circuit_open_until:
            logger.warning(
                "Notificación OSD suprimida por Cortacircuitos (abierto por %.1fs más)",
                self._circuit_open_until - now,
            )
            return False

        # 2. Protección anti-spam / debounce para evitar bucles o mensajes idénticos consecutivos
        key = (title, body)
        if not force and self._last_notification_key == key:
            if (now - self._last_notification_time) < self._debounce_window_sec:
                logger.debug("Notificación duplicada suprimida por debounce (%s)", key)
                return True

        # 3. Control de ráfagas para el cortacircuitos
        if not force:
            self._notification_timestamps = [
                t for t in self._notification_timestamps if (now - t) <= self._burst_window_sec
            ]
            if len(self._notification_timestamps) >= self._max_burst_count:
                self._circuit_open_until = now + self._circuit_cooldown_sec
                logger.warning(
                    "Cortacircuitos OSD activado: %d notificaciones en %.1fs. Modo silencioso temporal por %.1fs.",
                    len(self._notification_timestamps),
                    self._burst_window_sec,
                    self._circuit_cooldown_sec,
                )
                return False
            self._notification_timestamps.append(now)

        self._last_notification_key = key
        self._last_notification_time = now

        app_icon = icon or self._icon

        # 1. Intento primario vía llamada D-Bus personalizada o Gio.DBusConnection nativo
        if self._custom_dbus_call is not None:
            try:
                self._custom_dbus_call(title, body, app_icon, timeout_ms, synchronous_id)
                return True
            except Exception as e:
                logger.debug("Fallo en llamada personalizada a D-Bus: %s", e)
        else:
            conn = self._get_dbus_connection()
            if conn is not None:
                try:
                    from gi.repository import Gio, GLib

                    hints = {
                        "urgency": GLib.Variant("y", 1),
                        "transient": GLib.Variant("b", True),
                        "x-canonical-private-synchronous": GLib.Variant("s", synchronous_id),
                    }

                    params = GLib.Variant(
                        "(susssasa{sv}i)",
                        (
                            self._app_name,
                            0,
                            app_icon,
                            title,
                            body,
                            [],
                            hints,
                            timeout_ms,
                        ),
                    )

                    conn.call_sync(
                        "org.freedesktop.Notifications",
                        "/org/freedesktop/Notifications",
                        "org.freedesktop.Notifications",
                        "Notify",
                        params,
                        None,
                        Gio.DBusCallFlags.NONE,
                        1000,
                        None,
                    )
                    return True
                except Exception as e:
                    logger.debug("Error enviando notificación vía Gio D-Bus: %s", e)

        # 2. Fallback secundario vía comando notify-send
        try:
            cmd = [
                "notify-send",
                "-a", self._app_name,
                "-i", app_icon,
                "-t", str(timeout_ms),
                "-h", f"string:x-canonical-private-synchronous:{synchronous_id}",
                "-h", "boolean:transient:true",
                "-h", "byte:urgency:1",
                title,
                body,
            ]
            res = self._runner(cmd, capture_output=True, text=True, timeout=1.0)
            return getattr(res, "returncode", 0) == 0
        except subprocess.TimeoutExpired:
            logger.debug("notify-send excedió 1s; notificación descartada.")
            return False
        except Exception as e:
            logger.debug("Error ejecutando fallback notify-send: %s", e)
            return False

    def notify_profile_switched(
        self,
        app_name: str,
        profile_name: str,
        dpi: int,
        led_color: str | None = None,
        force: bool = False,
    ) -> bool:
        """
        Notifica al usuario que se activó un perfil para una aplicación/juego.
        """
        title = f"🎯 {app_name}"
        body = f"{_('Perfil:')} {profile_name}  •  {dpi:,} DPI"
        return self.send_notification(
            title=title,
            body=body,
            timeout_ms=1800,
            synchronous_id="g502-profile-change",
            force=force,
        )

    def notify_desktop_restored(self, dpi: int | None = None, force: bool = False) -> bool:
        """
        Notifica que se restauró el perfil estándar de escritorio.
        """
        title = f"🖥️ {_('Modo Escritorio')}"
        body = f"{_('Perfil de escritorio restaurado')}"
        if dpi:
            body += f"  •  {dpi:,} DPI"
        return self.send_notification(
            title=title,
            body=body,
            timeout_ms=1500,
            synchronous_id="g502-profile-change",
            force=force,
        )
