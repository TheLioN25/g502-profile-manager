"""
Ventana principal de la interfaz gráfica G502 Profile Manager (GTK4 + Libadwaita).
"""

from __future__ import annotations

from typing import Sequence

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, GLib, Gtk

from adapters.application_discovery_adapter import ApplicationDiscoveryAdapter
from adapters.ratbag_adapter import RatbagDeviceAdapter
from domain import Action, Application, Button, Profile
from gui.dialogs import ActionPickerDialog
from gui.mouse_diagram import G502MouseDiagram
from services.action_catalog import ActionCatalogService
from services.profile_manager import ProfileManager


BUTTON_DEFINITIONS = [
    ("Laterales", [
        ("G5", "Botón G5 (Lateral Delantero)", "go-next-symbolic"),
        ("G4", "Botón G4 (Lateral Trasero)", "go-previous-symbolic"),
        ("SNIPER", "Botón SNIPER (Pulgar / DPI Shift)", "crosshairs-symbolic"),
    ]),
    ("Superiores", [
        ("G7", "Botón G7 (DPI Down)", "go-down-symbolic"),
        ("G8", "Botón G8 (DPI Up)", "go-up-symbolic"),
        ("G9", "Botón G9 (Cambio de Perfil / Superior)", "preferences-system-symbolic"),
    ]),
    ("Rueda de Desplazamiento", [
        ("MIDDLE", "Clic Central (Rueda)", "input-mouse-symbolic"),
        ("WHEEL_LEFT", "Inclinación Rueda Izquierda", "pan-start-symbolic"),
        ("WHEEL_RIGHT", "Inclinación Rueda Derecha", "pan-end-symbolic"),
    ]),
    ("Clics Principales", [
        ("LEFT", "Clic Izquierdo", "input-mouse-symbolic"),
        ("RIGHT", "Clic Derecho", "input-mouse-symbolic"),
    ]),
]

QUICK_COLORS = [
    ("#00E5FF", "Cian Neón"),
    ("#0066FF", "Azul Eléctrico"),
    ("#FF0033", "Rojo Furia"),
    ("#00FF66", "Verde Logitech"),
    ("#9900FF", "Púrpura"),
    ("#FFCC00", "Ámbar"),
    ("#FFFFFF", "Blanco Puro"),
    ("#000000", "Apagado"),
]

QUICK_DPIS = [800, 1200, 1600, 2400, 3200, 8000, 12000, 16000]


class MainWindow(Adw.ApplicationWindow):
    """
    Ventana principal de configuración de perfiles para el ratón Logitech G502 HERO.
    """

    def __init__(
        self,
        app: Adw.Application,
        profile_manager: ProfileManager,
        catalog_service: ActionCatalogService,
        discovery_adapter: ApplicationDiscoveryAdapter,
        ratbag_adapter: RatbagDeviceAdapter | None = None,
    ):
        super().__init__(
            application=app,
            title="G502 Profile Manager",
            default_width=1160,
            default_height=740,
        )

        self._profile_manager = profile_manager
        self._catalog_service = catalog_service
        self._discovery_adapter = discovery_adapter
        self._ratbag_adapter = ratbag_adapter or RatbagDeviceAdapter()

        self._selected_app: Application | None = None
        self._current_profile: Profile | None = None
        self._app_rows: list[tuple[Gtk.ListBoxRow, Application]] = []
        self._button_rows: dict[str, tuple[Adw.ActionRow, Gtk.Label]] = {}

        # Contenedor Toast para notificaciones visuales
        self._toast_overlay = Adw.ToastOverlay()
        self.set_content(self._toast_overlay)

        # Estructura de división horizontal (Panel izquierdo y derecho)
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_position(320)
        paned.set_shrink_start_child(False)
        paned.set_shrink_end_child(False)
        self._toast_overlay.set_child(paned)

        # Construir panel izquierdo (Buscador y lista de juegos)
        left_panel = self._build_sidebar()
        paned.set_start_child(left_panel)

        # Construir panel derecho (Cabecera, pestañas y configuración)
        right_panel = self._build_main_content()
        paned.set_end_child(right_panel)

        # Cargar datos iniciales
        self._load_applications()
        self._update_mouse_hardware_status()

    # -------------------------------------------------------------------------
    # Panel Izquierdo: Sidebar de Juegos
    # -------------------------------------------------------------------------
    def _build_sidebar(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.set_size_request(300, -1)

        # Cabecera de la barra lateral
        sidebar_header = Adw.HeaderBar()
        sidebar_header.set_show_end_title_buttons(False)
        title = Adw.WindowTitle(title="Mis Juegos y Apps", subtitle="Instalados en el sistema")
        sidebar_header.set_title_widget(title)

        refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic", tooltip_text="Refrescar biblioteca")
        refresh_btn.connect("clicked", lambda _: self._load_applications())
        sidebar_header.pack_start(refresh_btn)
        box.append(sidebar_header)

        # Buscador de juegos
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        search_box.set_margin_start(12)
        search_box.set_margin_end(12)
        search_box.set_margin_top(8)
        search_box.set_margin_bottom(8)

        self._app_search_entry = Gtk.SearchEntry(placeholder_text="Buscar juego...")
        self._app_search_entry.set_hexpand(True)
        self._app_search_entry.connect("search-changed", self._on_app_search_changed)
        search_box.append(self._app_search_entry)
        box.append(search_box)

        # Lista de juegos instalados
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        box.append(scrolled)

        self._app_list_box = Gtk.ListBox()
        self._app_list_box.add_css_class("navigation-sidebar")
        self._app_list_box.connect("row-selected", self._on_app_row_selected)
        scrolled.set_child(self._app_list_box)

        return box

    # -------------------------------------------------------------------------
    # Panel Derecho: Contenido Principal
    # -------------------------------------------------------------------------
    def _build_main_content(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # HeaderBar del panel principal
        self._main_header = Adw.HeaderBar()
        self._window_title = Adw.WindowTitle(title="G502 Profile Manager", subtitle="Selecciona una aplicación")
        self._main_header.set_title_widget(self._window_title)

        # Indicador de estado del mouse
        self._mouse_status_label = Gtk.Label(label="Buscando mouse...")
        self._mouse_status_label.set_margin_end(8)
        self._main_header.pack_start(self._mouse_status_label)

        # Botón Aplicar al Mouse
        self._apply_mouse_btn = Gtk.Button(label="Aplicar al Ratón", tooltip_text="Escribir perfil directamente al G502 HERO")
        self._apply_mouse_btn.add_css_class("suggested-action")
        self._apply_mouse_btn.connect("clicked", self._on_apply_to_mouse_clicked)
        self._main_header.pack_end(self._apply_mouse_btn)

        # Botón Guardar
        self._save_btn = Gtk.Button(label="Guardar", tooltip_text="Guardar cambios del perfil")
        self._save_btn.connect("clicked", self._on_save_profile_clicked)
        self._main_header.pack_end(self._save_btn)

        box.append(self._main_header)

        # Barra de cambio de vista (ViewSwitcher)
        self._view_stack = Adw.ViewStack()
        self._view_stack.set_vexpand(True)

        switcher_bar = Adw.ViewSwitcher(
            stack=self._view_stack,
            policy=Adw.ViewSwitcherPolicy.WIDE,
        )
        switcher_bar.set_margin_top(6)
        switcher_bar.set_margin_bottom(6)
        box.append(switcher_bar)

        # 1. Vista de Botones
        buttons_view = self._build_buttons_view()
        self._view_stack.add_titled_with_icon(
            buttons_view,
            "buttons",
            "Botones",
            "input-mouse-symbolic",
        )

        # 2. Vista de Rendimiento (DPI)
        perf_view = self._build_performance_view()
        self._view_stack.add_titled_with_icon(
            perf_view,
            "performance",
            "Rendimiento (DPI)",
            "speedometer-symbolic",
        )

        # 3. Vista de Iluminación (LED RGB)
        lighting_view = self._build_lighting_view()
        self._view_stack.add_titled_with_icon(
            lighting_view,
            "lighting",
            "Iluminación LED",
            "weather-clear-symbolic",
        )

        box.append(self._view_stack)
        return box

    # -------------------------------------------------------------------------
    # Vistas de Contenido: Botones (Esquema Visual + Lista de Preferencias)
    # -------------------------------------------------------------------------
    def _build_buttons_view(self) -> Gtk.Widget:
        container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        container.set_margin_start(16)
        container.set_margin_end(16)
        container.set_margin_top(12)
        container.set_margin_bottom(12)

        # Columna Izquierda: Esquema Visual del Ratón Logitech G502 HERO
        diagram_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        diagram_box.set_size_request(440, -1)
        diagram_box.add_css_class("card")

        diagram_header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        diagram_header.set_margin_start(12)
        diagram_header.set_margin_top(8)

        diagram_title = Gtk.Label(label="Esquema Interactivo G502 HERO", xalign=0)
        diagram_title.add_css_class("heading")
        diagram_subtitle = Gtk.Label(label="Haz clic en cualquier botón del ratón para asignar una acción", xalign=0)
        diagram_subtitle.add_css_class("caption")
        diagram_subtitle.add_css_class("dim-label")

        diagram_header.append(diagram_title)
        diagram_header.append(diagram_subtitle)
        diagram_box.append(diagram_header)

        self._mouse_diagram = G502MouseDiagram(on_button_clicked=self._open_assign_dialog)
        diagram_box.append(self._mouse_diagram)
        container.append(diagram_box)

        # Columna Derecha: Lista de Botones por Preferencias
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)

        pref_page = Adw.PreferencesPage()
        scrolled.set_child(pref_page)

        for group_title, buttons in BUTTON_DEFINITIONS:
            group = Adw.PreferencesGroup(title=group_title)
            pref_page.add(group)

            for btn_id, btn_name, icon_name in buttons:
                row = Adw.ActionRow(title=btn_name, subtitle=f"ID: {btn_id}")
                row.add_prefix(Gtk.Image.new_from_icon_name(icon_name))

                # Pasar el cursor por la fila resalta el botón en el esquema del ratón
                motion = Gtk.EventControllerMotion()
                motion.connect("enter", lambda _c, _x, _y, bid=btn_id: self._mouse_diagram.highlight_button(bid))
                motion.connect("leave", lambda _c, bid=btn_id: self._mouse_diagram.highlight_button(None))
                row.add_controller(motion)

                # Chip que muestra la acción asignada
                chip = Gtk.Label(label="Sin asignar")
                chip.add_css_class("action-chip-empty")
                chip.set_valign(Gtk.Align.CENTER)
                row.add_suffix(chip)

                # Botón para asignar/cambiar
                assign_btn = Gtk.Button(label="Cambiar")
                assign_btn.set_valign(Gtk.Align.CENTER)
                assign_btn.connect("clicked", lambda _b, bid=btn_id, bname=btn_name: self._open_assign_dialog(bid, bname))
                row.add_suffix(assign_btn)

                group.add(row)
                self._button_rows[btn_id] = (row, chip)

        container.append(scrolled)
        return container

    # -------------------------------------------------------------------------
    # Vistas de Contenido: Rendimiento (DPI)
    # -------------------------------------------------------------------------
    def _build_performance_view(self) -> Gtk.Widget:
        scrolled = Gtk.ScrolledWindow()
        pref_page = Adw.PreferencesPage()
        scrolled.set_child(pref_page)

        dpi_group = Adw.PreferencesGroup(
            title="Sensibilidad del Sensor HERO 25K",
            description="Ajusta los puntos por pulgada (DPI) para una puntería precisa",
        )
        pref_page.add(dpi_group)

        # Fila con valor actual grande
        dpi_row = Adw.ActionRow(title="Sensibilidad Principal")
        self._dpi_display_label = Gtk.Label(label="8000 DPI")
        self._dpi_display_label.add_css_class("dpi-value-label")
        self._dpi_display_label.set_valign(Gtk.Align.CENTER)
        dpi_row.add_suffix(self._dpi_display_label)
        dpi_group.add(dpi_row)

        # Deslizador de DPI
        slider_row = Adw.PreferencesRow()
        slider_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        slider_box.set_margin_start(16)
        slider_box.set_margin_end(16)
        slider_box.set_margin_top(12)
        slider_box.set_margin_bottom(12)

        self._dpi_adjustment = Gtk.Adjustment(value=8000, lower=100, upper=25600, step_increment=50, page_increment=500)
        self._dpi_scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=self._dpi_adjustment)
        self._dpi_scale.set_digits(0)
        self._dpi_scale.set_hexpand(True)
        self._dpi_scale.connect("value-changed", self._on_dpi_slider_changed)
        slider_box.append(self._dpi_scale)

        # Botones de presets rápidos de DPI
        preset_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        preset_box.set_halign(Gtk.Align.CENTER)
        for dpi in QUICK_DPIS:
            btn = Gtk.Button(label=f"{dpi}")
            btn.connect("clicked", self._make_quick_dpi_handler(dpi))
            preset_box.append(btn)
        slider_box.append(preset_box)

        slider_row.set_child(slider_box)
        dpi_group.add(slider_row)

        # DPI Shift / Sniper
        shift_group = Adw.PreferencesGroup(
            title="Sensibilidad del Botón Sniper (DPI Shift)",
            description="Sensibilidad temporal activada al mantener presionado el botón pulgar",
        )
        pref_page.add(shift_group)

        shift_row = Adw.ActionRow(title="DPI de Francotirador")
        self._shift_dpi_adjustment = Gtk.Adjustment(value=400, lower=100, upper=25600, step_increment=50)
        self._shift_dpi_spin = Gtk.SpinButton(adjustment=self._shift_dpi_adjustment)
        self._shift_dpi_spin.set_valign(Gtk.Align.CENTER)
        self._shift_dpi_spin.connect("value-changed", self._on_shift_dpi_changed)
        shift_row.add_suffix(self._shift_dpi_spin)
        shift_group.add(shift_row)

        return scrolled

    # -------------------------------------------------------------------------
    # Vistas de Contenido: Iluminación LED
    # -------------------------------------------------------------------------
    def _build_lighting_view(self) -> Gtk.Widget:
        scrolled = Gtk.ScrolledWindow()
        pref_page = Adw.PreferencesPage()
        scrolled.set_child(pref_page)

        led_group = Adw.PreferencesGroup(
            title="Iluminación LIGHTSYNC RGB",
            description="Personaliza el color del logotipo G y el indicador DPI",
        )
        pref_page.add(led_group)

        # Fila de color actual
        color_row = Adw.ActionRow(title="Color de Iluminación")
        self._color_preview = Gtk.Box()
        self._color_preview.add_css_class("color-preview-box")
        self._color_preview.set_valign(Gtk.Align.CENTER)
        color_row.add_suffix(self._color_preview)

        self._color_hex_entry = Gtk.Entry(text="#00E5FF", max_length=7, width_chars=9)
        self._color_hex_entry.set_valign(Gtk.Align.CENTER)
        self._color_hex_entry.connect("changed", self._on_color_hex_changed)
        color_row.add_suffix(self._color_hex_entry)
        led_group.add(color_row)

        # Presets rápidos de color
        palette_row = Adw.PreferencesRow()
        palette_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        palette_box.set_margin_start(16)
        palette_box.set_margin_end(16)
        palette_box.set_margin_top(12)
        palette_box.set_margin_bottom(12)

        quick_label = Gtk.Label(label="Colores Recomendados:", xalign=0)
        quick_label.add_css_class("dim-label")
        palette_box.append(quick_label)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_box.set_halign(Gtk.Align.START)
        for hex_code, name in QUICK_COLORS:
            btn = Gtk.Button(tooltip_text=f"{name} ({hex_code})")
            btn.add_css_class("quick-color-btn")

            # Cuadrado coloreado dentro del botón
            swatch = Gtk.Box()
            swatch.set_size_request(24, 24)
            self._apply_box_background(swatch, hex_code)
            btn.set_child(swatch)

            btn.connect("clicked", self._make_quick_color_handler(hex_code))
            btn_box.append(btn)

        palette_box.append(btn_box)
        palette_row.set_child(palette_box)
        led_group.add(palette_row)

        self._update_color_preview("#00E5FF")
        return scrolled

    # -------------------------------------------------------------------------
    # Lógica de Datos y Eventos
    # -------------------------------------------------------------------------
    def _load_applications(self):
        """Descubre juegos instalados de Steam y Epic Games y llena la lista."""
        while child := self._app_list_box.get_first_child():
            self._app_list_box.remove(child)

        self._app_rows.clear()
        apps = self._discovery_adapter.discover_all_applications()
        self._catalog_service.sync_with_installed_applications(apps)

        first_row = None
        for app in apps:
            row = Gtk.ListBoxRow()
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            hbox.set_margin_start(12)
            hbox.set_margin_end(12)
            hbox.set_margin_top(8)
            hbox.set_margin_bottom(8)

            icon = Gtk.Image.new_from_icon_name("application-x-executable-symbolic")
            hbox.append(icon)

            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            name_label = Gtk.Label(label=app.name, xalign=0)
            name_label.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
            name_label.add_css_class("heading")
            vbox.append(name_label)

            id_label = Gtk.Label(label=app.application_id, xalign=0)
            id_label.add_css_class("caption")
            id_label.add_css_class("dim-label")
            vbox.append(id_label)
            hbox.append(vbox)

            # Badge si tiene perfil guardado
            existing = self._profile_manager.get_active_profile_for_application(app.application_id)
            if existing:
                badge = Gtk.Label(label="Configurado")
                badge.add_css_class("app-badge-preset")
                badge.set_valign(Gtk.Align.CENTER)
                badge.set_hexpand(True)
                badge.set_halign(Gtk.Align.END)
                hbox.append(badge)

            row.set_child(hbox)
            self._app_list_box.append(row)
            self._app_rows.append((row, app))

            if first_row is None or app.application_id == "steam:230410":
                first_row = row

        if first_row:
            self._app_list_box.select_row(first_row)

        self._show_toast("Biblioteca de aplicaciones sincronizada")

    def _on_app_row_selected(self, _box, row: Gtk.ListBoxRow | None):
        if not row:
            return

        for r, app in self._app_rows:
            if r == row:
                self._select_application(app)
                break

    def _select_application(self, app: Application):
        self._selected_app = app
        self._window_title.set_title(app.name)
        self._window_title.set_subtitle(f"ID: {app.application_id}")

        # Cargar perfil existente o crear uno en memoria
        profile = self._profile_manager.get_active_profile_for_application(app.application_id)
        if not profile:
            profile = Profile(
                name=f"{app.name} Perfil",
                application_id=app.application_id,
                dpi=8000,
                led_color="#00E5FF",
            )
        self._current_profile = profile

        # Actualizar campos en la interfaz
        self._dpi_adjustment.set_value(profile.dpi.dpi)
        self._dpi_display_label.set_text(f"{profile.dpi.dpi} DPI")

        if profile.dpi.shift_dpi:
            self._shift_dpi_adjustment.set_value(profile.dpi.shift_dpi)

        if profile.led_color:
            self._color_hex_entry.set_text(profile.led_color)
            self._update_color_preview(profile.led_color)

        # Actualizar botones
        self._refresh_button_assignments()

    def _refresh_button_assignments(self):
        if not self._current_profile:
            return

        for btn_id, (_row, chip) in self._button_rows.items():
            assignment = self._current_profile.get_assignment_for_button(btn_id)
            if assignment:
                action = assignment.action
                chip.set_text(f"{action.name} [{action.binding_value}]")
                chip.remove_css_class("action-chip-empty")
                chip.add_css_class("action-chip")
            else:
                chip.set_text("Sin asignar")
                chip.remove_css_class("action-chip")
                chip.add_css_class("action-chip-empty")

        if hasattr(self, "_mouse_diagram"):
            self._mouse_diagram.set_profile(self._current_profile)

    def _open_assign_dialog(self, btn_id: str, btn_name: str):
        if not self._selected_app or not self._current_profile:
            return

        categories = self._catalog_service.get_categories_for_application(self._selected_app.application_id)
        assignment = self._current_profile.get_assignment_for_button(btn_id)
        current_action = assignment.action if assignment else None

        def on_action_selected(action: Action | None):
            if action:
                self._current_profile.assign(Button(button_id=btn_id, name=btn_name), action)
                self._show_toast(f"Asignado '{action.name}' al {btn_name}")
            else:
                self._current_profile.unassign_button(btn_id)
                self._show_toast(f"Quitada asignación de {btn_name}")
            self._refresh_button_assignments()

        dialog = ActionPickerDialog(
            parent_window=self,
            button_id=btn_id,
            button_name=btn_name,
            app_id=self._selected_app.application_id,
            app_name=self._selected_app.name,
            categories=categories,
            current_action=current_action,
            on_action_selected=on_action_selected,
        )
        dialog.present()

    def _on_dpi_slider_changed(self, adjustment: Gtk.Adjustment):
        val = int(adjustment.get_value())
        self._dpi_display_label.set_text(f"{val} DPI")
        if self._current_profile:
            self._current_profile.set_dpi(val, self._current_profile.dpi.shift_dpi)

    def _make_quick_dpi_handler(self, dpi: int):
        def handler(_btn):
            self._dpi_adjustment.set_value(dpi)
        return handler

    def _on_shift_dpi_changed(self, spin: Gtk.SpinButton):
        val = int(spin.get_value())
        if self._current_profile:
            self._current_profile.set_dpi(self._current_profile.dpi.dpi, val)

    def _on_color_hex_changed(self, entry: Gtk.Entry):
        text = entry.get_text().strip()
        if len(text) == 7 and text.startswith("#"):
            try:
                self._update_color_preview(text)
                if self._current_profile:
                    self._current_profile.set_led_color(text)
            except Exception:
                pass

    def _make_quick_color_handler(self, hex_code: str):
        def handler(_btn):
            self._color_hex_entry.set_text(hex_code)
            self._update_color_preview(hex_code)
            if self._current_profile:
                self._current_profile.set_led_color(hex_code)
        return handler

    def _update_color_preview(self, hex_code: str):
        self._apply_box_background(self._color_preview, hex_code)
        if hasattr(self, "_mouse_diagram"):
            self._mouse_diagram.set_led_color(hex_code)

    def _apply_box_background(self, widget: Gtk.Widget, hex_code: str):
        safe_class = f"color-swatch-{hex_code.replace('#', '').lower()}"
        css_provider = Gtk.CssProvider()
        css = f".{safe_class} {{ background-color: {hex_code}; border-radius: 6px; }}"
        css_provider.load_from_string(css)
        display = Gdk.Display.get_default()
        if display:
            Gtk.StyleContext.add_provider_for_display(
                display,
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )
        widget.set_css_classes([safe_class, "color-preview-box"])

    def _on_save_profile_clicked(self, _btn):
        if not self._selected_app or not self._current_profile:
            return

        # Guardar en repositorio
        saved_profile = self._profile_manager.save_profile(self._current_profile)
        self._profile_manager.set_default_profile(self._selected_app.application_id, saved_profile.id)
        self._show_toast(f"Perfil guardado para {self._selected_app.name}")

    def _on_apply_to_mouse_clicked(self, _btn):
        if not self._current_profile:
            return

        try:
            success = self._ratbag_adapter.apply_profile(self._current_profile)
            if success:
                self._show_toast("¡Perfil aplicado con éxito al ratón G502 HERO!")
            else:
                self._show_toast("Advertencia: No se pudo aplicar completamente al hardware.")
        except Exception as e:
            self._show_toast(f"Error al comunicar con ratbagctl: {e}")

    def _update_mouse_hardware_status(self):
        try:
            device = self._ratbag_adapter.find_device()
            if device:
                self._mouse_status_label.set_text("● G502 HERO Conectado")
                self._mouse_status_label.remove_css_class("mouse-status-disconnected")
                self._mouse_status_label.add_css_class("mouse-status-connected")
            else:
                self._mouse_status_label.set_text("○ Ratón Desconectado")
                self._mouse_status_label.remove_css_class("mouse-status-connected")
                self._mouse_status_label.add_css_class("mouse-status-disconnected")
        except Exception:
            self._mouse_status_label.set_text("○ ratbagd no disponible")
            self._mouse_status_label.add_css_class("mouse-status-disconnected")

    def _on_app_search_changed(self, entry: Gtk.SearchEntry):
        query = entry.get_text().strip().casefold()
        for row, app in self._app_rows:
            if not query:
                row.set_visible(True)
            else:
                matches = query in app.name.casefold() or query in app.application_id.casefold()
                row.set_visible(matches)

    def _show_toast(self, message: str):
        toast = Adw.Toast.new(message)
        toast.set_timeout(3)
        self._toast_overlay.add_toast(toast)
