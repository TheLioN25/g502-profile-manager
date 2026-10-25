"""
Adaptador de notificaciones de escritorio y OSD para G502 Profile Manager.

Proporciona notificaciones discretas mediante D-Bus nativo (org.freedesktop.Notifications)
y fallback a notify-send para informar al usuario de cambios de perfil en pantalla completa.
"""

from __future__ import annotations

import logging
import subprocess
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
    ):
        self._enabled = enabled
        self._app_name = app_name
        self._icon = icon
        self._custom_dbus_call = dbus_call_sync
        self._runner = command_runner or subprocess.run
        self._dbus_conn = None
        self._dbus_init_attempted = False

    @property
    def enabled(self) -> bool:
        """Determina si las notificaciones OSD están habilitadas."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = bool(value)

    def _get_dbus_connection(self):
        if self._dbus_conn is not None or self._dbus_init_attempted:
            return self._dbus_conn

        self._dbus_init_attempted = True
        try:
            from gi.repository import Gio
            self._dbus_conn = Gio.bus_get_sync(Gio.BusType.SESSION, None)
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
    ) -> bool:
        """
        Envía una notificación discreta de escritorio.
        Configura hints transitorios para no interferir con juegos a pantalla completa.
        """
        if not self._enabled:
            return False

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
                "-h", "int:transient:1",
                "-h", "byte:urgency:1",
                title,
                body,
            ]
            res = self._runner(cmd, capture_output=True, text=True)
            return getattr(res, "returncode", 0) == 0
        except Exception as e:
            logger.debug("Error ejecutando fallback notify-send: %s", e)
            return False

    def notify_profile_switched(
        self,
        app_name: str,
        profile_name: str,
        dpi: int,
        led_color: str | None = None,
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
        )

    def notify_desktop_restored(self, dpi: int | None = None) -> bool:
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
        )
