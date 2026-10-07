"""
Módulo de indicador en la bandeja del sistema (System Tray) para Linux.

Implementa la especificación freedesktop/KDE StatusNotifierItem (SNI)
directamente sobre D-Bus utilizando Gio.DBusConnection, garantizando compatibilidad
nativa con GTK4 y Libadwaita sin colisiones de dependencias de GTK 3.0.
"""

from __future__ import annotations

import logging
from typing import Callable

import gi
from gi.repository import Gio, GLib

logger = logging.getLogger("g502.tray")

SNI_INTROSPECTION_XML = """
<node>
  <interface name="org.kde.StatusNotifierItem">
    <property name="Category" type="s" access="read"/>
    <property name="Id" type="s" access="read"/>
    <property name="Title" type="s" access="read"/>
    <property name="Status" type="s" access="read"/>
    <property name="IconName" type="s" access="read"/>
    <property name="ItemIsMenu" type="b" access="read"/>
    <property name="Menu" type="o" access="read"/>
    <property name="ToolTip" type="(sa(iiay)ss)" access="read"/>
    <method name="ContextMenu">
      <arg type="i" name="x" direction="in"/>
      <arg type="i" name="y" direction="in"/>
    </method>
    <method name="Activate">
      <arg type="i" name="x" direction="in"/>
      <arg type="i" name="y" direction="in"/>
    </method>
    <method name="SecondaryActivate">
      <arg type="i" name="x" direction="in"/>
      <arg type="i" name="y" direction="in"/>
    </method>
    <signal name="NewTitle"/>
    <signal name="NewIcon"/>
    <signal name="NewToolTip"/>
    <signal name="NewStatus">
      <arg type="s" name="status"/>
    </signal>
  </interface>
</node>
"""


class TrayIndicator:
    """
    Indicador para la bandeja del sistema basado en StatusNotifierItem.
    """

    def __init__(
        self,
        on_activate: Callable[[], None] | None = None,
        on_toggle_auto: Callable[[], None] | None = None,
        on_quit: Callable[[], None] | None = None,
    ):
        self._on_activate = on_activate
        self._on_toggle_auto = on_toggle_auto
        self._on_quit = on_quit

        self._bus: Gio.DBusConnection | None = None
        self._registration_id: int | None = None
        self._is_registered: bool = False

        self._icon_name: str = "io.github.thelion.G502ProfileManager"
        self._profile_name: str = "Escritorio / Sistema"
        self._app_name: str = "Escritorio"
        self._dpi: int = 1200
        self._auto_active: bool = False
        self._battery_level: int | None = None

        self._object_path = f"/StatusNotifierItem/{id(self)}"

        self._initialize_dbus()

    @property
    def is_available(self) -> bool:
        """Devuelve True si el tray está conectado exitosamente a D-Bus."""
        return self._is_registered

    def _initialize_dbus(self) -> None:
        """Conecta al bus de sesión y registra el StatusNotifierItem."""
        try:
            self._bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            if not self._bus:
                return

            node_info = Gio.DBusNodeInfo.new_for_xml(SNI_INTROSPECTION_XML)
            interface_info = node_info.interfaces[0]

            self._registration_id = self._bus.register_object(
                self._object_path,
                interface_info,
                self._handle_method_call,
                self._handle_get_property,
                None,
            )

            # Registrar ante el servicio de vigilancia de bandejas del entorno de escritorio
            self._bus.call_sync(
                "org.kde.StatusNotifierWatcher",
                "/StatusNotifierWatcher",
                "org.kde.StatusNotifierWatcher",
                "RegisterStatusNotifierItem",
                GLib.Variant("(s)", (self._object_path,)),
                None,
                Gio.DBusCallFlags.NONE,
                1000,
                None,
            )
            self._is_registered = True
            logger.info("TrayIndicator registrado exitosamente en D-Bus en %s.", self._object_path)
        except Exception as e:
            logger.debug("No se pudo registrar TrayIndicator en la bandeja del sistema: %s", e)
            self._is_registered = False

    def update_status(
        self,
        profile_name: str,
        app_name: str,
        dpi: int = 1200,
        auto_active: bool = False,
        battery_level: int | None = None,
    ) -> None:
        """
        Actualiza los datos expuestos en el Tooltip y emite la señal de refresco.
        """
        self._profile_name = profile_name
        self._app_name = app_name
        self._dpi = dpi
        self._auto_active = auto_active
        self._battery_level = battery_level

        if self._bus and self._is_registered:
            try:
                self._bus.emit_signal(
                    None,
                    self._object_path,
                    "org.kde.StatusNotifierItem",
                    "NewToolTip",
                    None,
                )
            except Exception as e:
                logger.debug("Error al emitir NewToolTip en TrayIndicator: %s", e)

    def _handle_method_call(
        self,
        connection: Gio.DBusConnection,
        sender: str,
        path: str,
        interface: str,
        method: str,
        params: GLib.Variant,
        invocation: Gio.DBusMethodInvocation,
    ) -> None:
        """Maneja las invocaciones de métodos desde el panel de escritorio."""
        if method in ("Activate", "ContextMenu"):
            if self._on_activate:
                GLib.idle_add(self._on_activate)
        elif method == "SecondaryActivate":
            if self._on_toggle_auto:
                GLib.idle_add(self._on_toggle_auto)
            elif self._on_activate:
                GLib.idle_add(self._on_activate)

        invocation.return_value(None)

    def _handle_get_property(
        self,
        connection: Gio.DBusConnection,
        sender: str,
        path: str,
        interface: str,
        prop_name: str,
    ) -> GLib.Variant | None:
        """Devuelve las propiedades requeridas por la especificación SNI."""
        if prop_name == "Category":
            return GLib.Variant("s", "Hardware")
        elif prop_name == "Id":
            return GLib.Variant("s", "io.github.thelion.G502ProfileManager")
        elif prop_name == "Title":
            return GLib.Variant("s", "G502 Profile Manager")
        elif prop_name == "Status":
            return GLib.Variant("s", "Active")
        elif prop_name == "IconName":
            return GLib.Variant("s", self._icon_name)
        elif prop_name == "ItemIsMenu":
            return GLib.Variant("b", False)
        elif prop_name == "Menu":
            return GLib.Variant("o", "/NO_DBUSMENU")
        elif prop_name == "ToolTip":
            auto_str = "Auto: Activo" if self._auto_active else "Auto: Inactivo"
            title = f"G502: {self._profile_name}"
            bat_str = f" | 🔋 {self._battery_level}%" if self._battery_level is not None else ""
            desc = f"{self._app_name} | {self._dpi} DPI{bat_str} | {auto_str}"
            return GLib.Variant("(sa(iiay)ss)", (self._icon_name, [], title, desc))
        return None

    def destroy(self) -> None:
        """Desregistra el objeto D-Bus al salir."""
        if self._bus and self._registration_id:
            try:
                self._bus.unregister_object(self._registration_id)
            except Exception:
                pass
            self._registration_id = None
            self._is_registered = False
