"""
Ventana principal de la interfaz gráfica G502 Profile Manager (GTK4 + Libadwaita).
"""

from __future__ import annotations

import threading
from typing import Sequence

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, GLib, Gtk, Pango

from adapters.application_discovery_adapter import ApplicationDiscoveryAdapter
from adapters.ratbag_adapter import RatbagDeviceAdapter
from domain import Action, Application, Button, DEFAULT_VARIANT, DeviceVariant, DpiConfiguration, Profile
from i18n import _, get_language, set_language, get_available_languages

REDDIT_COMMUNITY_URL = "https://www.reddit.com/r/G502MasterRace/comments/1wwvyk5/i_built_a_native_gtk4_libadwaita_profile_manager/"
GITHUB_ISSUES_URL = "https://github.com/TheLioN25/g502-profile-manager/issues"

from engine import AutomationEngine
from gui.dialogs import ActionPickerDialog, NewProfileDialog
from gui.mouse_diagram import G502MouseDiagram
from gui.tray import TrayIndicator
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
    ("#0022FF", "Azul Eléctrico Puro"),
    ("#FF0033", "Rojo Furia"),
    ("#00FF66", "Verde Logitech"),
    ("#5500DD", "Púrpura Real"),
    ("#FFCC00", "Ámbar"),
    ("#FFE5C8", "Blanco Neutro (Calibrado)"),
    ("#FFFFFF", "Blanco Frío"),
    ("#000000", "Apagado"),
]

LED_MODE_OPTIONS = [
    ("on", "Estático"),
    ("breathing", "Respiración (Pulsación)"),
    ("cycle", "Ciclo de Espectro (Arcoíris)"),
    ("off", "Apagado"),
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
        automation_engine: AutomationEngine | None = None,
        start_auto: bool = False,
        preview_hero_banner: bool = False,
    ):
        super().__init__(
            application=app,
            title="G502 Profile Manager",
            default_width=1240,
            default_height=780,
        )
        self.set_icon_name("io.github.thelion.G502ProfileManager")
        self.set_size_request(880, 560)

        self._profile_manager = profile_manager
        self._catalog_service = catalog_service
        self._discovery_adapter = discovery_adapter
        self._ratbag_adapter = ratbag_adapter or RatbagDeviceAdapter()
        self._preview_hero_banner: bool = preview_hero_banner
        self._current_variant: DeviceVariant = DEFAULT_VARIANT
        self._automation_engine: AutomationEngine | None = automation_engine
        self._auto_thread: threading.Thread | None = None
        self.connect("close-request", self._on_close_request)

        self._selected_app: Application | None = None
        self._current_profile: Profile | None = None
        self._current_app_profiles: list[Profile] = []
        self._updating_profile_dropdown: bool = False
        self._updating_lighting_ui: bool = False
        self._app_rows: list[tuple[Gtk.ListBoxRow, Application]] = []
        self._configured_rows: list[tuple[Gtk.ListBoxRow, Application]] = []
        self._unconfigured_rows: list[tuple[Gtk.ListBoxRow, Application]] = []
        self._button_rows: dict[str, tuple[Adw.ActionRow, Gtk.Label]] = {}
        self._button_pref_groups: list[tuple[Adw.PreferencesGroup, str]] = []
        self._button_row_widgets: dict[str, tuple[Adw.ActionRow, Gtk.Label, Gtk.Button, str]] = {}

        # Inicializar indicador de bandeja del sistema (System Tray)
        try:
            self._tray = TrayIndicator(
                on_activate=self._on_tray_activate,
                on_toggle_auto=self._on_tray_toggle_auto,
            )
        except Exception:
            self._tray = None

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
        self._check_systemd_service_status()
        if start_auto and not self._auto_switch.get_active():
            self._auto_switch.set_active(True)

    # -------------------------------------------------------------------------
    # Panel Izquierdo: Sidebar de Juegos
    # -------------------------------------------------------------------------
    def _build_sidebar(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.set_size_request(300, -1)

        # Cabecera de la barra lateral
        sidebar_header = Adw.HeaderBar()
        sidebar_header.set_show_end_title_buttons(False)
        self._sidebar_title = Adw.WindowTitle(title=_("Mis Juegos y Apps"), subtitle=_("Instalados en el sistema"))
        title = self._sidebar_title
        sidebar_header.set_title_widget(title)

        self._sidebar_refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic", tooltip_text=_("Refrescar biblioteca"))
        refresh_btn = self._sidebar_refresh_btn
        refresh_btn.connect("clicked", lambda _: self._load_applications())
        sidebar_header.pack_start(refresh_btn)
        box.append(sidebar_header)

        # 1. Sección Superior: Perfiles Configurados
        configured_scrolled = Gtk.ScrolledWindow()
        configured_scrolled.set_propagate_natural_height(True)
        configured_scrolled.set_max_content_height(240)
        configured_scrolled.set_hexpand(True)

        self._configured_list_box = Gtk.ListBox()
        self._configured_list_box.add_css_class("navigation-sidebar")
        self._configured_list_box.connect("row-selected", self._on_configured_row_selected)
        configured_scrolled.set_child(self._configured_list_box)
        box.append(configured_scrolled)

        # 2. Línea separadora
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        separator.set_margin_top(4)
        separator.set_margin_bottom(4)
        box.append(separator)

        # 3. Buscador de aplicaciones disponibles
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        search_box.set_margin_start(12)
        search_box.set_margin_end(12)
        search_box.set_margin_top(2)
        search_box.set_margin_bottom(6)

        self._app_search_entry = Gtk.SearchEntry(placeholder_text=_("Buscar juego o app..."))
        self._app_search_entry.set_hexpand(True)
        self._app_search_entry.connect("search-changed", self._on_app_search_changed)
        search_box.append(self._app_search_entry)
        box.append(search_box)

        # 4. Sección Inferior: Aplicaciones no configuradas
        unconfigured_scrolled = Gtk.ScrolledWindow()
        unconfigured_scrolled.set_vexpand(True)
        unconfigured_scrolled.set_hexpand(True)

        self._unconfigured_list_box = Gtk.ListBox()
        self._unconfigured_list_box.add_css_class("navigation-sidebar")
        self._unconfigured_list_box.connect("row-selected", self._on_unconfigured_row_selected)
        unconfigured_scrolled.set_child(self._unconfigured_list_box)
        box.append(unconfigured_scrolled)

        # Mantener referencia por compatibilidad
        self._app_list_box = self._configured_list_box

        return box

    # -------------------------------------------------------------------------
    # Panel Derecho: Contenido Principal
    # -------------------------------------------------------------------------
    def _build_main_content(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # HeaderBar del panel principal
        self._main_header = Adw.HeaderBar()
        self._window_title = Adw.WindowTitle(title=_("G502 Profile Manager"), subtitle=_("Selecciona una aplicación"))
        self._main_header.set_title_widget(self._window_title)

        # Indicador de estado del mouse
        self._mouse_status_label = Gtk.Label(label=_("Buscando mouse..."))
        self._mouse_status_label.set_margin_end(8)
        self._main_header.pack_start(self._mouse_status_label)

        # Separador visual
        header_sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        header_sep.set_margin_start(4)
        header_sep.set_margin_end(6)
        self._main_header.pack_start(header_sep)

        # Interruptor de Auto-Detección de Juegos
        self._auto_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._auto_box.add_css_class("auto-switch-box")
        self._auto_box.set_tooltip_text(_("Conmutación automática de perfiles según el juego o aplicación activa"))

        auto_icon = Gtk.Image.new_from_icon_name("media-flash-symbolic")
        self._auto_box.append(auto_icon)

        self._auto_label = Gtk.Label(label=_("Auto-Perfil"))
        auto_label = self._auto_label
        auto_label.add_css_class("auto-switch-label")
        self._auto_box.append(auto_label)

        self._auto_switch = Gtk.Switch()
        self._auto_switch.set_valign(Gtk.Align.CENTER)
        self._auto_switch.connect("notify::active", self._on_auto_switch_toggled)
        self._auto_box.append(self._auto_switch)

        self._main_header.pack_start(self._auto_box)

        # Botón Aplicar al Mouse
        self._apply_mouse_btn = Gtk.Button(label=_("Aplicar al Ratón"), tooltip_text=_("Escribir perfil directamente al G502 HERO"))
        self._apply_mouse_btn.add_css_class("suggested-action")
        self._apply_mouse_btn.connect("clicked", self._on_apply_to_mouse_clicked)

        # Botón Guardar
        self._save_btn = Gtk.Button(label=_("Guardar"), tooltip_text=_("Guardar cambios del perfil"))
        self._save_btn.connect("clicked", self._on_save_profile_clicked)

        # Controles de Gestión de Perfiles
        profile_controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        profile_controls.set_margin_end(6)

        self._profile_string_list = Gtk.StringList.new([])
        self._profile_dropdown = Gtk.DropDown.new(self._profile_string_list, None)
        self._profile_dropdown.set_tooltip_text(_("Seleccionar perfil para este juego"))
        self._profile_dropdown.connect("notify::selected", self._on_profile_dropdown_changed)
        profile_controls.append(self._profile_dropdown)

        self._new_profile_btn = Gtk.Button(icon_name="list-add-symbolic", tooltip_text=_("Crear nuevo perfil"))
        self._new_profile_btn.connect("clicked", self._on_new_profile_clicked)
        profile_controls.append(self._new_profile_btn)

        self._profile_menu_btn = Gtk.MenuButton(icon_name="view-more-symbolic", tooltip_text=_("Opciones del perfil"))
        self._profile_popover = Gtk.Popover()
        pop_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        pop_box.set_margin_top(6)
        pop_box.set_margin_bottom(6)
        pop_box.set_margin_start(6)
        pop_box.set_margin_end(6)

        self._set_def_btn = Gtk.Button(label=_("⭐ Marcar como Predeterminado"))
        set_def_btn = self._set_def_btn
        set_def_btn.add_css_class("flat")
        set_def_btn.connect("clicked", self._on_set_default_profile_clicked)
        pop_box.append(set_def_btn)

        self._dup_btn = Gtk.Button(label=_("📋 Duplicar Perfil"))
        dup_btn = self._dup_btn
        dup_btn.add_css_class("flat")
        dup_btn.connect("clicked", self._on_duplicate_profile_clicked)
        pop_box.append(dup_btn)

        self._del_btn = Gtk.Button(label=_("🗑️ Eliminar Perfil"))
        del_btn = self._del_btn
        del_btn.add_css_class("flat")
        del_btn.add_css_class("destructive-action")
        del_btn.connect("clicked", self._on_delete_profile_clicked)
        pop_box.append(del_btn)

        self._profile_popover.set_child(pop_box)
        self._profile_menu_btn.set_popover(self._profile_popover)
        profile_controls.append(self._profile_menu_btn)

        # Selector de Idioma (ES / EN)
        self._lang_menu_btn = Gtk.MenuButton(
            icon_name="preferences-desktop-locale-symbolic",
            tooltip_text=_("Cambiar idioma"),
        )
        self._lang_popover = Gtk.Popover()
        lang_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        lang_box.set_margin_top(6)
        lang_box.set_margin_bottom(6)
        lang_box.set_margin_start(6)
        lang_box.set_margin_end(6)

        lang_es_btn = Gtk.Button(label="🇪🇸 Español")
        lang_es_btn.add_css_class("flat")
        lang_es_btn.connect("clicked", lambda _: self._on_change_language("es"))
        lang_box.append(lang_es_btn)

        lang_en_btn = Gtk.Button(label="🇺🇸 English")
        lang_en_btn.add_css_class("flat")
        lang_en_btn.connect("clicked", lambda _: self._on_change_language("en"))
        lang_box.append(lang_en_btn)

        self._lang_popover.set_child(lang_box)
        self._lang_menu_btn.set_popover(self._lang_popover)

        self._main_header.pack_end(self._lang_menu_btn)
        self._main_header.pack_end(self._apply_mouse_btn)
        self._main_header.pack_end(self._save_btn)
        self._main_header.pack_end(profile_controls)

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
        self._buttons_stack_page = self._view_stack.add_titled_with_icon(
            buttons_view,
            "buttons",
            _("Botones"),
            "input-mouse-symbolic",
        )

        # 2. Vista de Rendimiento (DPI)
        perf_view = self._build_performance_view()
        self._perf_stack_page = self._view_stack.add_titled_with_icon(
            perf_view,
            "performance",
            _("Rendimiento (DPI)"),
            "speedometer-symbolic",
        )

        # 3. Vista de Iluminación (LED RGB)
        lighting_view = self._build_lighting_view()
        self._lighting_stack_page = self._view_stack.add_titled_with_icon(
            lighting_view,
            "lighting",
            _("Iluminación LED"),
            "weather-clear-symbolic",
        )

        box.append(self._view_stack)
        return box

    # -------------------------------------------------------------------------
    # Vistas de Contenido: Botones (Esquema Visual + Lista de Preferencias)
    # -------------------------------------------------------------------------
    def _build_buttons_view(self) -> Gtk.Widget:
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_margin_start(16)
        paned.set_margin_end(16)
        paned.set_margin_top(12)
        paned.set_margin_bottom(12)
        paned.set_position(520)
        paned.set_shrink_start_child(False)
        paned.set_shrink_end_child(False)
        paned.set_resize_start_child(True)
        paned.set_resize_end_child(True)

        # Columna Izquierda: Esquema Visual del Ratón Logitech G502 HERO
        diagram_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        diagram_box.set_size_request(380, -1)
        diagram_box.set_hexpand(True)
        diagram_box.set_vexpand(True)
        diagram_box.add_css_class("card")

        diagram_header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        diagram_header.set_margin_start(16)
        diagram_header.set_margin_end(16)
        diagram_header.set_margin_top(12)
        diagram_header.set_margin_bottom(4)

        self._diagram_title = Gtk.Label(label=_("Esquema Interactivo G502 HERO"), xalign=0)
        diagram_title = self._diagram_title
        diagram_title.add_css_class("heading")
        self._diagram_subtitle = Gtk.Label(label=_("Haz clic en cualquier botón del ratón para asignar una acción"), xalign=0)
        diagram_subtitle = self._diagram_subtitle
        diagram_subtitle.add_css_class("caption")
        diagram_subtitle.add_css_class("dim-label")

        diagram_header.append(diagram_title)
        diagram_header.append(diagram_subtitle)
        diagram_box.append(diagram_header)

        self._mouse_diagram = G502MouseDiagram(on_button_clicked=self._open_assign_dialog)
        self._mouse_diagram.set_hexpand(True)
        self._mouse_diagram.set_vexpand(True)
        diagram_box.append(self._mouse_diagram)
        paned.set_start_child(diagram_box)

        # Columna Derecha: Lista de Botones por Preferencias
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        scrolled.set_min_content_width(360)
        scrolled.set_margin_start(12)

        pref_page = Adw.PreferencesPage()
        scrolled.set_child(pref_page)

        self._button_pref_groups.clear()
        self._button_row_widgets.clear()

        for group_title, buttons in BUTTON_DEFINITIONS:
            group = Adw.PreferencesGroup(title=_(group_title))
            self._button_pref_groups.append((group, group_title))
            pref_page.add(group)

            for btn_id, btn_name, icon_name in buttons:
                row = Adw.ActionRow(title=_(btn_name), subtitle=f"ID: {btn_id}")
                row.set_title_lines(1)
                row.set_subtitle_lines(1)
                row.add_prefix(Gtk.Image.new_from_icon_name(icon_name))

                # Pasar el cursor por la fila resalta el botón en el esquema del ratón
                motion = Gtk.EventControllerMotion()
                motion.connect("enter", lambda _c, _x, _y, bid=btn_id: self._mouse_diagram.highlight_button(bid))
                motion.connect("leave", lambda _c, bid=btn_id: self._mouse_diagram.highlight_button(None))
                row.add_controller(motion)

                # Chip que muestra la acción asignada
                chip = Gtk.Label(label=_("Sin asignar"))
                chip.add_css_class("action-chip-empty")
                chip.set_valign(Gtk.Align.CENTER)
                chip.set_ellipsize(Pango.EllipsizeMode.END)
                chip.set_max_width_chars(18)
                row.add_suffix(chip)

                # Botón para asignar/cambiar
                assign_btn = Gtk.Button(label=_("Cambiar"))
                assign_btn.set_valign(Gtk.Align.CENTER)
                assign_btn.connect("clicked", lambda _b, bid=btn_id, bname=btn_name: self._open_assign_dialog(bid, bname))
                row.add_suffix(assign_btn)

                group.add(row)
                self._button_rows[btn_id] = (row, chip)
                self._button_row_widgets[btn_id] = (row, chip, assign_btn, btn_name)

        # Banner / Tarjeta de Soporte Comunitario para la familia Logitech
        self._community_group = Adw.PreferencesGroup()
        self._community_group.set_title(_("Comunidad y Calibración"))
        self._community_group.set_margin_top(24)
        self._community_group.set_margin_bottom(12)

        self._community_banner = Adw.Banner(
            title=_("Soporte experimental: Ayúdanos a calibrar este modelo reportando cualquier anomalía.")
        )
        self._community_banner.set_button_label(_("Dar Feedback / Reportar"))
        self._community_banner.connect("button-clicked", self._on_report_community_issue)
        self._community_banner.add_css_class("community-banner-card")
        self._community_banner.set_revealed(False)
        self._community_group.add(self._community_banner)
        self._community_group.set_visible(False)
        pref_page.add(self._community_group)

        paned.set_end_child(scrolled)
        return paned

    # -------------------------------------------------------------------------
    # Vistas de Contenido: Rendimiento (DPI)
    # -------------------------------------------------------------------------
    def _build_performance_view(self) -> Gtk.Widget:
        scrolled = Gtk.ScrolledWindow()
        pref_page = Adw.PreferencesPage()
        scrolled.set_child(pref_page)

        self._dpi_group = Adw.PreferencesGroup(
            title=_("Sensibilidad del Sensor HERO 25K"),
            description=_("Ajusta los puntos por pulgada (DPI) para una puntería precisa"),
        )
        dpi_group = self._dpi_group
        pref_page.add(dpi_group)

        # Fila con valor actual grande
        self._dpi_row = Adw.ActionRow(title=_("Sensibilidad Principal"))
        dpi_row = self._dpi_row
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
        self._shift_group = Adw.PreferencesGroup(
            title=_("Sensibilidad del Botón Sniper (DPI Shift)"),
            description=_("Sensibilidad temporal activada al mantener presionado el botón pulgar"),
        )
        shift_group = self._shift_group
        pref_page.add(shift_group)

        self._shift_row = Adw.ActionRow(title=_("DPI de Francotirador"))
        shift_row = self._shift_row
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
            title=_("Iluminación LIGHTSYNC RGB"),
            description=_("Personaliza el modo, color y efectos del logotipo G e indicador DPI"),
        )
        self._led_group = led_group
        pref_page.add(led_group)

        # 1. Selector de Modo de Iluminación
        self._led_mode_row = Adw.ComboRow(title=_("Efecto de Iluminación"))
        mode_strings = [_(name) for _mid, name in LED_MODE_OPTIONS]
        self._led_mode_row.set_model(Gtk.StringList.new(mode_strings))
        self._led_mode_row.connect("notify::selected", self._on_led_mode_row_changed)
        led_group.add(self._led_mode_row)

        # 2. Fila de color actual y selector interactivo
        self._color_row = Adw.ActionRow(
            title=_("Color de Iluminación"),
            subtitle=_("Haz clic en la muestra para abrir la paleta o introduce el código hexadecimal"),
        )

        self._color_dialog = Gtk.ColorDialog()
        self._color_dialog.set_with_alpha(False)
        self._color_dialog_btn = Gtk.ColorDialogButton(dialog=self._color_dialog)
        self._color_dialog_btn.set_valign(Gtk.Align.CENTER)
        self._color_dialog_btn.set_tooltip_text(_("Selector de color interactivo"))
        self._color_dialog_btn.connect("notify::rgba", self._on_color_dialog_rgba_changed)
        self._color_row.add_suffix(self._color_dialog_btn)
        self._color_preview = self._color_dialog_btn

        self._color_hex_entry = Gtk.Entry(text="#00E5FF", max_length=7, width_chars=9)
        self._color_hex_entry.set_valign(Gtk.Align.CENTER)
        self._color_hex_entry.connect("changed", self._on_color_hex_changed)
        self._color_row.add_suffix(self._color_hex_entry)
        led_group.add(self._color_row)

        # 3. Presets rápidos de color (calibrados para G502 HERO)
        self._palette_row = Adw.PreferencesRow()
        palette_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        palette_box.set_margin_start(16)
        palette_box.set_margin_end(16)
        palette_box.set_margin_top(12)
        palette_box.set_margin_bottom(12)

        self._palette_label = Gtk.Label(label=_("Colores Calibrados G502:"), xalign=0)
        self._palette_label.add_css_class("dim-label")
        palette_box.append(self._palette_label)

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
        self._palette_row.set_child(palette_box)
        led_group.add(self._palette_row)

        # 4. Velocidad / Duración del Efecto (para Respiración y Ciclo de Espectro)
        self._duration_row = Adw.ActionRow(
            title=_("Velocidad del Efecto"),
            subtitle=_("Duración de cada pulsación o ciclo de color"),
        )
        self._duration_display_label = Gtk.Label(label="2.0 s (2000 ms)")
        self._duration_display_label.set_valign(Gtk.Align.CENTER)
        self._duration_display_label.add_css_class("dim-label")
        self._duration_row.add_suffix(self._duration_display_label)
        led_group.add(self._duration_row)

        self._duration_slider_row = Adw.PreferencesRow()
        duration_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        duration_box.set_margin_start(16)
        duration_box.set_margin_end(16)
        duration_box.set_margin_top(12)
        duration_box.set_margin_bottom(12)

        self._duration_adjustment = Gtk.Adjustment(
            value=2000,
            lower=500,
            upper=10000,
            step_increment=100,
            page_increment=500,
        )
        self._duration_scale = Gtk.Scale(
            orientation=Gtk.Orientation.HORIZONTAL,
            adjustment=self._duration_adjustment,
        )
        self._duration_scale.set_digits(0)
        self._duration_scale.set_hexpand(True)
        self._duration_scale.connect("value-changed", self._on_duration_slider_changed)
        duration_box.append(self._duration_scale)

        # Botones de presets de velocidad
        duration_presets_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        duration_presets_box.set_halign(Gtk.Align.CENTER)
        self._duration_preset_buttons = []
        speed_presets = [
            (1000, "1s (Rápido)"),
            (2000, "2s (Normal)"),
            (3000, "3s (Suave)"),
            (5000, "5s (Lento)"),
            (10000, "10s (Relax)"),
        ]
        for ms, label_text in speed_presets:
            d_btn = Gtk.Button(label=_(label_text))
            d_btn.connect("clicked", self._make_quick_duration_handler(ms))
            duration_presets_box.append(d_btn)
            self._duration_preset_buttons.append((d_btn, label_text))
        duration_box.append(duration_presets_box)

        self._duration_slider_row.set_child(duration_box)
        led_group.add(self._duration_slider_row)

        self._update_color_preview("#00E5FF")
        self._update_lighting_sensitivity("on")
        return scrolled

    # -------------------------------------------------------------------------
    # Lógica de Datos y Eventos
    # -------------------------------------------------------------------------
    def _create_app_row(self, app: Application, is_configured: bool) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        hbox.set_margin_start(12)
        hbox.set_margin_end(12)
        hbox.set_margin_top(8)
        hbox.set_margin_bottom(8)

        icon_name = (
            "user-desktop-symbolic"
            if app.application_id == "desktop:general"
            else "application-x-executable-symbolic"
        )
        icon = Gtk.Image.new_from_icon_name(icon_name)
        hbox.append(icon)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        display_name = _(app.name) if app.application_id == "desktop:general" else app.name
        name_label = Gtk.Label(label=display_name, xalign=0)
        name_label.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
        name_label.add_css_class("heading")
        vbox.append(name_label)

        id_label = Gtk.Label(label=app.application_id, xalign=0)
        id_label.add_css_class("caption")
        id_label.add_css_class("dim-label")
        vbox.append(id_label)
        hbox.append(vbox)

        if is_configured:
            badge = Gtk.Label(label=_("Configurado"))
            badge.add_css_class("app-badge-preset")
            badge.set_valign(Gtk.Align.CENTER)
            badge.set_hexpand(True)
            badge.set_halign(Gtk.Align.END)
            hbox.append(badge)

        row.set_child(hbox)
        return row

    def _load_applications(self, select_app_id: str | None = None):
        """Descubre juegos instalados y organiza las secciones de configuradas (arriba) y no configuradas (abajo)."""
        while child := self._configured_list_box.get_first_child():
            self._configured_list_box.remove(child)
        while child := self._unconfigured_list_box.get_first_child():
            self._unconfigured_list_box.remove(child)

        self._app_rows.clear()
        self._configured_rows.clear()
        self._unconfigured_rows.clear()

        apps = self._discovery_adapter.discover_all_applications()
        self._catalog_service.sync_with_installed_applications(apps)

        selected_row_to_activate = None
        first_configured_row = None
        first_unconfigured_row = None

        for app in apps:
            existing = self._profile_manager.get_active_profile_for_application(app.application_id)
            is_configured = existing is not None or app.application_id == "desktop:general"

            row = self._create_app_row(app, is_configured=is_configured)

            if is_configured:
                self._configured_list_box.append(row)
                self._configured_rows.append((row, app))
                if first_configured_row is None:
                    first_configured_row = row
            else:
                self._unconfigured_list_box.append(row)
                self._unconfigured_rows.append((row, app))
                if first_unconfigured_row is None:
                    first_unconfigured_row = row

            self._app_rows.append((row, app))

            if select_app_id and app.application_id == select_app_id:
                selected_row_to_activate = (row, is_configured)

        if selected_row_to_activate:
            row, is_conf = selected_row_to_activate
            if is_conf:
                self._configured_list_box.select_row(row)
            else:
                self._unconfigured_list_box.select_row(row)
        elif first_configured_row:
            self._configured_list_box.select_row(first_configured_row)
        elif first_unconfigured_row:
            self._unconfigured_list_box.select_row(first_unconfigured_row)

        self._show_toast(_("Biblioteca de aplicaciones sincronizada"))

    def _on_configured_row_selected(self, _box, row: Gtk.ListBoxRow | None):
        if not row:
            return
        self._unconfigured_list_box.unselect_all()
        for r, app in self._configured_rows:
            if r == row:
                pending_pid = getattr(self, "_pending_profile_id_to_select", None)
                self._select_application(app, select_profile_id=pending_pid)
                break

    def _on_unconfigured_row_selected(self, _box, row: Gtk.ListBoxRow | None):
        if not row:
            return
        self._configured_list_box.unselect_all()
        for r, app in self._unconfigured_rows:
            if r == row:
                pending_pid = getattr(self, "_pending_profile_id_to_select", None)
                self._select_application(app, select_profile_id=pending_pid)
                break

    def _on_app_row_selected(self, _box, row: Gtk.ListBoxRow | None):
        if not row:
            return
        for r, app in self._app_rows:
            if r == row:
                self._select_application(app)
                break

    def _select_application(self, app: Application, select_profile_id: str | None = None):
        self._selected_app = app
        display_name = _(app.name) if app.application_id == "desktop:general" else app.name
        self._window_title.set_title(display_name)
        self._window_title.set_subtitle(f"ID: {app.application_id}")
        self._populate_profiles_dropdown(app.application_id, select_profile_id=select_profile_id)

    def select_application_by_id(self, app_id: str, profile_id: str | None = None) -> bool:
        """Selecciona una aplicación por su ID en la barra lateral y carga su perfil en la interfaz."""
        target_row = None
        target_app = None
        is_configured = False

        for row, app in self._configured_rows:
            if app.application_id == app_id:
                target_row = row
                target_app = app
                is_configured = True
                break

        if not target_app:
            for row, app in self._unconfigured_rows:
                if app.application_id == app_id:
                    target_row = row
                    target_app = app
                    is_configured = False
                    break

        if not target_app:
            return False

        self._pending_profile_id_to_select = profile_id

        if is_configured:
            self._unconfigured_list_box.unselect_all()
            self._configured_list_box.select_row(target_row)
        else:
            self._configured_list_box.unselect_all()
            self._unconfigured_list_box.select_row(target_row)

        if not self._selected_app or self._selected_app.application_id != app_id or (profile_id and self._current_profile and self._current_profile.id != profile_id):
            self._select_application(target_app, select_profile_id=profile_id)

        self._pending_profile_id_to_select = None
        return True

    def _populate_profiles_dropdown(self, application_id: str, select_profile_id: str | None = None):
        """Llena el desplegable de perfiles asociados a la aplicación."""
        self._updating_profile_dropdown = True
        try:
            profiles = list(self._profile_manager.get_profiles_for_application(application_id))
            if not profiles:
                app_label = _(self._selected_app.name) if self._selected_app and self._selected_app.application_id == "desktop:general" else (self._selected_app.name if self._selected_app else _("Juego"))
                default_name = f"{app_label} {_('Perfil')}"
                new_p = self._profile_manager.create_profile(
                    name=default_name,
                    application_id=application_id,
                    dpi=8000,
                    led_color="#00E5FF",
                    led_mode="on",
                    led_duration=None,
                )
                profiles = [new_p]

            self._current_app_profiles = profiles
            default_p = self._profile_manager.get_default_profile(application_id)
            default_id = default_p.id if default_p else profiles[0].id

            string_list = Gtk.StringList.new([])
            target_id = select_profile_id or default_id
            selected_idx = 0

            for idx, p in enumerate(profiles):
                is_default = (p.id == default_id)
                display_name = f"⭐ {p.name}" if is_default else p.name
                string_list.append(display_name)
                if p.id == target_id:
                    selected_idx = idx

            self._profile_dropdown.set_model(string_list)
            self._profile_dropdown.set_selected(selected_idx)

            active_profile = profiles[selected_idx]
            self._load_profile_into_ui(active_profile)
        finally:
            self._updating_profile_dropdown = False

    def _load_profile_into_ui(self, profile: Profile):
        """Carga los datos de un perfil en todos los widgets de la interfaz."""
        self._current_profile = profile

        # Actualizar campos en la interfaz
        self._dpi_adjustment.set_value(profile.dpi.dpi)
        self._dpi_display_label.set_text(f"{profile.dpi.dpi} DPI")

        if profile.dpi.shift_dpi:
            self._shift_dpi_adjustment.set_value(profile.dpi.shift_dpi)

        self._updating_lighting_ui = True
        try:
            mode = getattr(profile, "led_mode", "on")
            mode_idx = 0
            for idx, (m, _mname) in enumerate(LED_MODE_OPTIONS):
                if m == mode:
                    mode_idx = idx
                    break
            self._led_mode_row.set_selected(mode_idx)

            duration = getattr(profile, "led_duration", None) or 2000
            self._duration_adjustment.set_value(duration)
            self._duration_display_label.set_text(f"{duration/1000:.1f} s ({int(duration)} ms)")

            if profile.led_color:
                self._color_hex_entry.set_text(profile.led_color)
                self._update_color_preview(profile.led_color)

            self._update_lighting_sensitivity(mode)
        finally:
            self._updating_lighting_ui = False

        # Actualizar botones y esquema vectorial
        self._refresh_button_assignments()
        self._sync_tray()

    def _refresh_button_assignments(self):
        if not self._current_profile:
            return

        for btn_id, (_row, chip) in self._button_rows.items():
            assignment = self._current_profile.get_assignment_for_button(btn_id)
            if assignment:
                action = assignment.action
                text = f"{action.name} [{action.binding_value}]"
                chip.set_text(text)
                chip.set_tooltip_text(text)
                chip.remove_css_class("action-chip-empty")
                chip.add_css_class("action-chip")
            else:
                chip.set_text(_("Sin asignar"))
                chip.set_tooltip_text(_("Sin acción asignada"))
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
                self._show_toast(_("Asignado '{action}' al {button}").format(action=action.name, button=_(btn_name)))
            else:
                self._current_profile.unassign_button(btn_id)
                self._show_toast(_("Quitada asignación de {button}").format(button=_(btn_name)))
            self._refresh_button_assignments()

        dialog = ActionPickerDialog(
            parent_window=self,
            button_id=btn_id,
            button_name=_(btn_name),
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
            self._current_profile.set_dpi(DpiConfiguration(val, self._current_profile.dpi.shift_dpi))

    def _make_quick_dpi_handler(self, dpi: int):
        def handler(_btn):
            self._dpi_adjustment.set_value(dpi)
        return handler

    def _on_shift_dpi_changed(self, spin: Gtk.SpinButton):
        val = int(spin.get_value())
        if self._current_profile:
            self._current_profile.set_dpi(DpiConfiguration(self._current_profile.dpi.dpi, val))

    def _adapt_ui_to_variant(self, variant: DeviceVariant):
        self._current_variant = variant
        max_dpi = variant.capabilities.max_dpi
        if hasattr(self, "_dpi_adjustment"):
            self._dpi_adjustment.set_upper(max_dpi)
        if hasattr(self, "_shift_dpi_adjustment"):
            self._shift_dpi_adjustment.set_upper(max_dpi)

        if hasattr(self, "_led_group"):
            if not variant.capabilities.has_lighting:
                self._led_group.set_description(
                    _("Iluminación no disponible en {short_name} (modelo sin iluminación RGB)").format(
                        short_name=variant.short_name
                    )
                )
            elif not variant.capabilities.has_rgb:
                self._led_group.set_description(
                    _("Iluminación monocromo azul (1 zona) en {short_name}").format(
                        short_name=variant.short_name
                    )
                )
            else:
                self._led_group.set_description(
                    _("Personaliza el modo, color y efectos del logotipo G e indicadores DPI ({zones} zonas)").format(
                        zones=variant.capabilities.led_zones
                    )
                )

        if hasattr(self, "_led_mode_row"):
            selected_idx = self._led_mode_row.get_selected()
            mode = LED_MODE_OPTIONS[selected_idx][0] if selected_idx < len(LED_MODE_OPTIONS) else "on"
            self._update_lighting_sensitivity(mode)

        # Activar banner de soporte experimental solo si no es el G502 HERO (o modo vista previa local)
        if hasattr(self, "_community_banner"):
            show_banner = (variant.key != "g502_hero") or getattr(self, "_preview_hero_banner", False)
            if show_banner:
                self._community_banner.set_title(
                    _("Soporte experimental para {short_name}: Ayúdanos a calibrarlo reportando cualquier anomalía.").format(
                        short_name=variant.short_name
                    )
                )
                self._community_banner.set_revealed(True)
                if hasattr(self, "_community_group"):
                    self._community_group.set_visible(True)
            else:
                self._community_banner.set_revealed(False)
                if hasattr(self, "_community_group"):
                    self._community_group.set_visible(False)

    def _update_lighting_sensitivity(self, mode: str):
        if hasattr(self, "_current_variant"):
            if not self._current_variant.capabilities.has_lighting:
                self._led_mode_row.set_sensitive(False)
                self._color_row.set_sensitive(False)
                self._palette_row.set_sensitive(False)
                if hasattr(self, "_duration_row"):
                    self._duration_row.set_sensitive(False)
                if hasattr(self, "_duration_slider_row"):
                    self._duration_slider_row.set_sensitive(False)
                return
            elif not self._current_variant.capabilities.has_rgb:
                self._led_mode_row.set_sensitive(True)
                self._color_row.set_sensitive(False)
                self._palette_row.set_sensitive(False)
                has_duration = (mode in ("breathing", "cycle"))
                if hasattr(self, "_duration_row"):
                    self._duration_row.set_sensitive(has_duration)
                if hasattr(self, "_duration_slider_row"):
                    self._duration_slider_row.set_sensitive(has_duration)
                return

        is_off = (mode == "off")
        is_cycle = (mode == "cycle")
        has_duration = (mode in ("breathing", "cycle"))

        color_sensitive = not (is_off or is_cycle)
        self._color_row.set_sensitive(color_sensitive)
        self._palette_row.set_sensitive(color_sensitive)

        self._duration_row.set_sensitive(has_duration)
        self._duration_slider_row.set_sensitive(has_duration)

    def _on_led_mode_row_changed(self, row: Adw.ComboRow, _pspec):
        if getattr(self, "_updating_lighting_ui", False):
            return
        selected_idx = row.get_selected()
        if 0 <= selected_idx < len(LED_MODE_OPTIONS):
            mode = LED_MODE_OPTIONS[selected_idx][0]
        else:
            mode = "on"

        self._update_lighting_sensitivity(mode)
        if self._current_profile:
            duration = int(self._duration_adjustment.get_value()) if mode in ("breathing", "cycle") else None
            self._current_profile.set_led_mode(mode, duration)

    def _on_duration_slider_changed(self, adjustment: Gtk.Adjustment):
        val = int(adjustment.get_value())
        self._duration_display_label.set_text(f"{val/1000:.1f} s ({val} ms)")
        if getattr(self, "_updating_lighting_ui", False):
            return
        if self._current_profile:
            mode = getattr(self._current_profile, "led_mode", "on")
            if mode in ("breathing", "cycle"):
                self._current_profile.set_led_mode(mode, val)

    def _make_quick_duration_handler(self, ms: int):
        def handler(_btn):
            self._duration_adjustment.set_value(ms)
        return handler

    def _on_color_dialog_rgba_changed(self, btn: Gtk.ColorDialogButton, _pspec):
        if getattr(self, "_updating_lighting_ui", False):
            return
        rgba = btn.get_rgba()
        r = int(round(rgba.red * 255))
        g = int(round(rgba.green * 255))
        b = int(round(rgba.blue * 255))
        hex_code = f"#{r:02X}{g:02X}{b:02X}"

        self._updating_lighting_ui = True
        try:
            self._color_hex_entry.set_text(hex_code)
        finally:
            self._updating_lighting_ui = False

        self._update_color_preview(hex_code, update_dialog=False)
        if self._current_profile:
            self._current_profile.set_led_color(hex_code)

    def _on_color_hex_changed(self, entry: Gtk.Entry):
        if getattr(self, "_updating_lighting_ui", False):
            return
        text = entry.get_text().strip().upper()
        if len(text) == 7 and text.startswith("#"):
            try:
                self._update_color_preview(text, update_dialog=True)
                if self._current_profile:
                    self._current_profile.set_led_color(text)
            except Exception:
                pass

    def _make_quick_color_handler(self, hex_code: str):
        def handler(_btn):
            self._updating_lighting_ui = True
            try:
                self._color_hex_entry.set_text(hex_code)
            finally:
                self._updating_lighting_ui = False
            self._update_color_preview(hex_code, update_dialog=True)
            if self._current_profile:
                self._current_profile.set_led_color(hex_code)
        return handler

    def _update_color_preview(self, hex_code: str, update_dialog: bool = True):
        if update_dialog and hasattr(self, "_color_dialog_btn"):
            try:
                rgba = Gdk.RGBA()
                if rgba.parse(hex_code):
                    self._updating_lighting_ui = True
                    try:
                        self._color_dialog_btn.set_rgba(rgba)
                    finally:
                        self._updating_lighting_ui = False
            except Exception:
                pass

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

    def _on_profile_dropdown_changed(self, dropdown, _param):
        if self._updating_profile_dropdown:
            return

        idx = dropdown.get_selected()
        if 0 <= idx < len(self._current_app_profiles):
            selected_profile = self._current_app_profiles[idx]
            self._load_profile_into_ui(selected_profile)
            self._show_toast(_("Perfil activo: {name}").format(name=selected_profile.name))

    def _on_new_profile_clicked(self, _btn):
        if not self._selected_app:
            return

        def on_created(name: str):
            new_p = self._profile_manager.create_profile(
                name=name,
                application_id=self._selected_app.application_id,
                dpi=self._current_profile.dpi.dpi if self._current_profile else 8000,
                led_color=self._current_profile.led_color if self._current_profile else "#00E5FF",
                led_mode=self._current_profile.led_mode if self._current_profile else "on",
                led_duration=self._current_profile.led_duration if self._current_profile else None,
            )
            self._populate_profiles_dropdown(self._selected_app.application_id, select_profile_id=new_p.id)
            self._show_toast(_("Perfil '{name}' creado.").format(name=name))

        dialog = NewProfileDialog(
            parent_window=self,
            app_name=self._selected_app.name,
            on_profile_created=on_created,
        )
        dialog.present()

    def _on_set_default_profile_clicked(self, _btn):
        if not self._selected_app or not self._current_profile:
            return

        self._profile_popover.popdown()
        self._profile_manager.set_default_profile(self._selected_app.application_id, self._current_profile.id)
        self._populate_profiles_dropdown(self._selected_app.application_id, select_profile_id=self._current_profile.id)
        self._show_toast(_("'{name}' marcado como predeterminado ⭐").format(name=self._current_profile.name))

    def _on_duplicate_profile_clicked(self, _btn):
        if not self._selected_app or not self._current_profile:
            return

        self._profile_popover.popdown()
        cloned = self._profile_manager.duplicate_profile(
            self._current_profile.id,
            f"{self._current_profile.name} (Copia)",
        )
        self._populate_profiles_dropdown(self._selected_app.application_id, select_profile_id=cloned.id)
        self._show_toast(_("Perfil duplicado: '{name}'").format(name=cloned.name))

    def _on_delete_profile_clicked(self, _btn):
        if not self._selected_app or not self._current_profile:
            return

        self._profile_popover.popdown()
        if len(self._current_app_profiles) <= 1:
            self._show_toast(_("No puedes eliminar el único perfil de este juego."))
            return

        deleted_name = self._current_profile.name
        self._profile_manager.delete_profile(self._current_profile.id)
        self._current_profile = None
        self._populate_profiles_dropdown(self._selected_app.application_id)
        self._show_toast(_("Perfil '{name}' eliminado.").format(name=deleted_name))
        self._load_applications(select_app_id=self._selected_app.application_id)

    def _on_save_profile_clicked(self, _btn):
        if not self._selected_app or not self._current_profile:
            return

        # Guardar en repositorio
        saved_profile = self._profile_manager.save_profile(self._current_profile)
        self._populate_profiles_dropdown(self._selected_app.application_id, select_profile_id=saved_profile.id)
        self._show_toast(_("Perfil '{name}' guardado.").format(name=saved_profile.name))
        self._load_applications(select_app_id=self._selected_app.application_id)

    def _on_report_community_issue(self, _banner):
        variant_name = getattr(self._current_variant, "short_name", "G502")
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading=_("Ayúdanos a Mejorar y Calibrar tu Ratón"),
            body=_(
                "Has conectado un {variant_name}. El soporte para este modelo se basa en especificaciones de libratbag "
                "y tu experiencia real es clave para seguir perfeccionándolo.\n\n"
                "¿Dónde te gustaría compartir tu opinión o reportar alguna anomalía?\n\n"
                "• Reddit: Ideal para comentar rápido en la comunidad sin necesidad de conocimientos de desarrollo.\n"
                "• GitHub: Recomendado para reportes técnicos detallados y seguimiento de bugs."
            ).format(variant_name=variant_name),
        )
        dialog.add_response("cancel", _("Cancelar"))
        dialog.add_response("github", "🐙 GitHub Issues")
        dialog.add_response("reddit", _("💬 Abrir en Reddit"))
        dialog.set_response_appearance("reddit", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("reddit")

        def on_response(_d, response_id):
            if response_id == "reddit":
                try:
                    Gtk.show_uri(self, REDDIT_COMMUNITY_URL, Gdk.CURRENT_TIME)
                except Exception:
                    pass
            elif response_id == "github":
                try:
                    Gtk.show_uri(self, GITHUB_ISSUES_URL, Gdk.CURRENT_TIME)
                except Exception:
                    pass

        dialog.connect("response", on_response)
        dialog.present()

    def _on_apply_to_mouse_clicked(self, _btn):
        if not self._current_profile:
            return

        target_profile = self._current_profile
        self._apply_mouse_btn.set_sensitive(False)
        self._apply_mouse_btn.set_label(_("Aplicando..."))

        def worker():
            msg = _("¡Perfil aplicado con éxito al ratón!")
            try:
                device = self._ratbag_adapter.find_device()
                if not device:
                    msg = _("Error: No se detectó ningún ratón de la familia G502 conectado.")
                else:
                    success = self._ratbag_adapter.apply_profile(device, target_profile)
                    variant_name = getattr(self._current_variant, "short_name", "G502")
                    if not success:
                        msg = _("Advertencia: No se pudo aplicar completamente al ratón {variant_name}.").format(variant_name=variant_name)
                    else:
                        msg = _("¡Perfil aplicado con éxito al ratón {variant_name}!").format(variant_name=variant_name)
            except Exception as e:
                msg = _("Error al comunicar con ratbagctl: {error}").format(error=e)

            def on_done():
                self._apply_mouse_btn.set_sensitive(True)
                self._apply_mouse_btn.set_label(_("Aplicar al Ratón"))
                self._show_toast(msg)
                return False

            GLib.idle_add(on_done)

        threading.Thread(target=worker, daemon=True).start()

    def _update_mouse_hardware_status(self):
        try:
            device = self._ratbag_adapter.find_device()
            if device:
                variant = None
                if hasattr(self._ratbag_adapter, "detect_device_variant"):
                    res = self._ratbag_adapter.detect_device_variant(device)
                    if isinstance(res, DeviceVariant):
                        variant = res
                if variant is None:
                    variant = DEFAULT_VARIANT

                self._current_variant = variant

                bat_text = ""
                if variant.capabilities.has_battery and hasattr(self._ratbag_adapter, "get_cached_battery_level"):
                    bat = self._ratbag_adapter.get_cached_battery_level(device, ttl_seconds=30.0)
                    if isinstance(bat, int):
                        bat_text = f" (🔋 {bat}%)"

                self._mouse_status_label.set_text(f"● {variant.short_name} {_('Conectado')}{bat_text}")
                self._mouse_status_label.remove_css_class("mouse-status-disconnected")
                self._mouse_status_label.add_css_class("mouse-status-connected")
                self._adapt_ui_to_variant(variant)
            else:
                self._mouse_status_label.set_text(_("○ Ratón Desconectado"))
                self._mouse_status_label.remove_css_class("mouse-status-connected")
                self._mouse_status_label.add_css_class("mouse-status-disconnected")
        except Exception:
            self._mouse_status_label.set_text(_("○ ratbagd no disponible"))
            self._mouse_status_label.add_css_class("mouse-status-disconnected")


    def _on_change_language(self, lang_code: str) -> None:
        if hasattr(self, "_lang_popover") and self._lang_popover:
            self._lang_popover.popdown()
        if get_language() == lang_code:
            return
        set_language(lang_code, persist=True)
        if hasattr(self, "_selected_app") and self._selected_app:
            self._load_applications(select_app_id=self._selected_app.application_id)
        else:
            self._load_applications(select_app_id="desktop:general")
        self._update_ui_texts()
        self._show_toast(_("Idioma cambiado exitosamente."))

    def _update_ui_texts(self) -> None:
        # Títulos de ventana y cabecera
        if hasattr(self, "_window_title"):
            self._window_title.set_title(_("G502 Profile Manager"))
            if not self._selected_app:
                self._window_title.set_subtitle(_("Selecciona una aplicación"))

        if hasattr(self, "_auto_box"):
            self._auto_box.set_tooltip_text(_("Conmutación automática de perfiles según el juego o aplicación activa"))
        if hasattr(self, "_auto_label"):
            self._auto_label.set_label(_("Auto-Perfil"))

        if hasattr(self, "_apply_mouse_btn"):
            self._apply_mouse_btn.set_label(_("Aplicar al Ratón"))
            self._apply_mouse_btn.set_tooltip_text(_("Escribir perfil directamente al G502 HERO"))
        if hasattr(self, "_save_btn"):
            self._save_btn.set_label(_("Guardar"))
            self._save_btn.set_tooltip_text(_("Guardar cambios del perfil"))

        if hasattr(self, "_profile_dropdown"):
            self._profile_dropdown.set_tooltip_text(_("Seleccionar perfil para este juego"))
        if hasattr(self, "_new_profile_btn"):
            self._new_profile_btn.set_tooltip_text(_("Crear nuevo perfil"))
        if hasattr(self, "_profile_menu_btn"):
            self._profile_menu_btn.set_tooltip_text(_("Opciones del perfil"))

        if hasattr(self, "_set_def_btn"):
            self._set_def_btn.set_label(_("⭐ Marcar como Predeterminado"))
        if hasattr(self, "_dup_btn"):
            self._dup_btn.set_label(_("📋 Duplicar Perfil"))
        if hasattr(self, "_del_btn"):
            self._del_btn.set_label(_("🗑️ Eliminar Perfil"))

        if hasattr(self, "_lang_menu_btn"):
            self._lang_menu_btn.set_tooltip_text(_("Cambiar idioma"))

        if hasattr(self, "_community_group"):
            self._community_group.set_title(_("Comunidad y Calibración"))

        if hasattr(self, "_community_banner"):
            variant_name = getattr(self._current_variant, "short_name", "G502")
            if hasattr(self, "_current_variant") and (self._current_variant.key != "g502_hero" or getattr(self, "_preview_hero_banner", False)):
                self._community_banner.set_title(
                    _("Soporte experimental para {short_name}: Ayúdanos a calibrarlo reportando cualquier anomalía.").format(
                        short_name=variant_name
                    )
                )
            else:
                self._community_banner.set_title(_("Soporte experimental: Ayúdanos a calibrar este modelo reportando cualquier anomalía."))
            self._community_banner.set_button_label(_("Dar Feedback / Reportar"))

        # Pestañas del ViewStack
        if hasattr(self, "_buttons_stack_page"):
            self._buttons_stack_page.set_title(_("Botones"))
        if hasattr(self, "_perf_stack_page"):
            self._perf_stack_page.set_title(_("Rendimiento (DPI)"))
        if hasattr(self, "_lighting_stack_page"):
            self._lighting_stack_page.set_title(_("Iluminación LED"))

        # Sidebar y búsqueda
        if hasattr(self, "_sidebar_title"):
            self._sidebar_title.set_title(_("Mis Juegos y Apps"))
            self._sidebar_title.set_subtitle(_("Instalados en el sistema"))
        if hasattr(self, "_sidebar_refresh_btn"):
            self._sidebar_refresh_btn.set_tooltip_text(_("Refrescar biblioteca"))
        if hasattr(self, "_app_search_entry"):
            self._app_search_entry.set_placeholder_text(_("Buscar juego o app..."))

        # Diagrama y textos
        if hasattr(self, "_diagram_title"):
            self._diagram_title.set_label(_("Esquema Interactivo G502 HERO"))
        if hasattr(self, "_diagram_subtitle"):
            self._diagram_subtitle.set_label(_("Haz clic en cualquier botón del ratón para asignar una acción"))

        # Actualizar grupos y filas de la columna de botones
        if hasattr(self, "_button_pref_groups"):
            for grp, gtitle in self._button_pref_groups:
                grp.set_title(_(gtitle))
        if hasattr(self, "_button_row_widgets"):
            for btn_id, (row, chip, assign_btn, btn_name) in self._button_row_widgets.items():
                row.set_title(_(btn_name))
                assign_btn.set_label(_("Cambiar"))
        self._refresh_button_assignments()

        # Actualizar vista de DPI
        if hasattr(self, "_dpi_group"):
            self._dpi_group.set_title(_("Sensibilidad del Sensor HERO 25K"))
            self._dpi_group.set_description(_("Ajusta los puntos por pulgada (DPI) para una puntería precisa"))
        if hasattr(self, "_dpi_row"):
            self._dpi_row.set_title(_("Sensibilidad Principal"))
        if hasattr(self, "_shift_group"):
            self._shift_group.set_title(_("Sensibilidad del Botón Sniper (DPI Shift)"))
            self._shift_group.set_description(_("Sensibilidad temporal activada al mantener presionado el botón pulgar"))
        if hasattr(self, "_shift_row"):
            self._shift_row.set_title(_("DPI de Francotirador"))

        # Actualizar vista de Iluminación LED
        if hasattr(self, "_led_group"):
            self._led_group.set_title(_("Iluminación LIGHTSYNC RGB"))
            self._led_group.set_description(_("Personaliza el modo, color y efectos del logotipo G e indicador DPI"))
        if hasattr(self, "_led_mode_row"):
            self._led_mode_row.set_title(_("Efecto de Iluminación"))
            curr_sel = self._led_mode_row.get_selected()
            self._updating_lighting_ui = True
            try:
                self._led_mode_row.set_model(Gtk.StringList.new([_(name) for _mid, name in LED_MODE_OPTIONS]))
                self._led_mode_row.set_selected(curr_sel)
            finally:
                self._updating_lighting_ui = False
        if hasattr(self, "_color_row"):
            self._color_row.set_title(_("Color de Iluminación"))
            self._color_row.set_subtitle(_("Haz clic en la muestra para abrir la paleta o introduce el código hexadecimal"))
        if hasattr(self, "_duration_row"):
            self._duration_row.set_title(_("Velocidad del Efecto"))
            self._duration_row.set_subtitle(_("Duración de cada pulsación o ciclo de color"))

        # Actualizar paleta calibrada y botones de velocidad
        if hasattr(self, "_palette_label"):
            self._palette_label.set_label(_("Colores Calibrados G502:"))
        if hasattr(self, "_color_dialog_btn"):
            self._color_dialog_btn.set_tooltip_text(_("Selector de color interactivo"))
        if hasattr(self, "_duration_preset_buttons"):
            for d_btn, label_text in self._duration_preset_buttons:
                d_btn.set_label(_(label_text))
        if hasattr(self, "_current_variant") and self._current_variant:
            self._adapt_ui_to_variant(self._current_variant)

        # Redibujar diagrama vectorial
        if hasattr(self, "_mouse_diagram"):
            self._mouse_diagram.queue_draw()

        # Refrescar sidebar (para insignias Configured / Configurado)
        self._load_applications()

        # Actualizar indicador de hardware en la cabecera
        self._update_mouse_hardware_status()

    def _on_app_search_changed(self, entry: Gtk.SearchEntry):
        query = entry.get_text().strip().casefold()
        for row, app in self._unconfigured_rows:
            if not query:
                row.set_visible(True)
            else:
                matches = query in app.name.casefold() or query in app.application_id.casefold()
                row.set_visible(matches)

    def _show_toast(self, message: str):
        toast = Adw.Toast.new(message)
        toast.set_timeout(3)
        self._toast_overlay.add_toast(toast)

    def _is_systemd_service_active(self) -> bool:
        import subprocess
        try:
            res = subprocess.run(
                ["systemctl", "--user", "is-active", "g502-profile-manager.service"],
                capture_output=True,
                text=True,
                check=False,
            )
            return res.stdout.strip() == "active"
        except Exception:
            return False

    def _check_systemd_service_status(self):
        if self._is_systemd_service_active():
            self._systemd_was_active = True
            import subprocess
            try:
                subprocess.run(["systemctl", "--user", "stop", "g502-profile-manager.service"], check=False)
            except Exception:
                pass
            self._auto_box.set_tooltip_text("Auto-detección activa con sincronización en tiempo real")
            self._auto_box.add_css_class("auto-switch-active")
            self._auto_switch.set_active(True)

    def _on_auto_switch_toggled(self, switch: Gtk.Switch, _pspec):
        from pathlib import Path
        import subprocess

        svc_file = Path.home() / ".config/systemd/user/g502-profile-manager.service"
        is_svc_installed = svc_file.exists()

        if switch.get_active():
            if is_svc_installed and self._is_systemd_service_active():
                try:
                    subprocess.run(["systemctl", "--user", "stop", "g502-profile-manager.service"], check=False)
                except Exception:
                    pass
            self._start_automation()
        else:
            self._systemd_was_active = False
            self._stop_automation()
            if is_svc_installed and self._is_systemd_service_active():
                try:
                    subprocess.run(["systemctl", "--user", "stop", "g502-profile-manager.service"], check=False)
                except Exception:
                    pass

    def _start_automation(self):
        self._auto_box.add_css_class("auto-switch-active")
        if self._automation_engine is None:
            self._automation_engine = AutomationEngine(
                profile_manager=self._profile_manager,
                device_adapter=self._ratbag_adapter,
                catalog_service=self._catalog_service,
                discovery_adapter=self._discovery_adapter,
                check_interval=2.0,
                on_profile_applied=lambda app_name, prof: GLib.idle_add(self._on_auto_profile_applied, app_name, prof),
                on_desktop_restored=lambda: GLib.idle_add(self._on_auto_desktop_restored),
                logger=lambda msg: None,
            )
        else:
            self._automation_engine._on_profile_applied = lambda app_name, prof: GLib.idle_add(self._on_auto_profile_applied, app_name, prof)
            self._automation_engine._on_desktop_restored = lambda: GLib.idle_add(self._on_auto_desktop_restored)

        def run_worker():
            if self._automation_engine:
                self._automation_engine.run()

        self._auto_thread = threading.Thread(target=run_worker, daemon=True)
        self._auto_thread.start()
        self._show_toast(_("⚡ Auto-detección activada: supervisando procesos..."))

    def _stop_automation(self):
        self._auto_box.remove_css_class("auto-switch-active")
        if self._automation_engine:
            self._automation_engine.stop()
        self._auto_thread = None
        self._on_auto_desktop_restored()
        self._show_toast(_("Auto-detección desactivada: modo escritorio restaurado."))

    def _on_auto_profile_applied(self, app_name: str, profile: Profile):
        self.select_application_by_id(profile.application_id, profile.id)
        self._window_title.set_subtitle(f"⚡ Auto: {app_name} ({profile.name} · {profile.dpi.dpi} DPI)")
        self._sync_tray()
        return False

    def _on_auto_desktop_restored(self):
        if not self.select_application_by_id("desktop:general"):
            if self._selected_app:
                self._window_title.set_subtitle(f"ID: {self._selected_app.application_id}")
            else:
                self._window_title.set_subtitle("Selecciona una aplicación")
        else:
            self._window_title.set_subtitle("⚡ Modo Escritorio (Perfil por defecto)")
        self._sync_tray()
        return False

    def _on_tray_activate(self):
        self.present()

    def _on_tray_toggle_auto(self):
        if hasattr(self, "_auto_switch"):
            self._auto_switch.set_active(not self._auto_switch.get_active())

    def _sync_tray(self):
        if not hasattr(self, "_tray") or self._tray is None:
            return
        prof_name = self._current_profile.name if self._current_profile else "Escritorio"
        app_name = _(self._selected_app.name) if self._selected_app and self._selected_app.application_id == "desktop:general" else (self._selected_app.name if self._selected_app else _("Sistema"))
        dpi = self._current_profile.dpi.dpi if self._current_profile else 1200
        auto_active = self._auto_switch.get_active() if hasattr(self, "_auto_switch") else False
        battery_level = None
        if hasattr(self, "_current_variant") and self._current_variant.capabilities.has_battery:
            if hasattr(self, "_ratbag_adapter") and hasattr(self._ratbag_adapter, "get_cached_battery_level"):
                dev = self._ratbag_adapter.find_device()
                if dev:
                    bat = self._ratbag_adapter.get_cached_battery_level(dev)
                    if isinstance(bat, int):
                        battery_level = bat
        self._tray.update_status(
            profile_name=prof_name,
            app_name=app_name,
            dpi=dpi,
            auto_active=auto_active,
            battery_level=battery_level,
        )

    def _on_close_request(self, _window) -> bool:
        auto_was_active = hasattr(self, "_auto_switch") and self._auto_switch.get_active()
        if self._auto_thread is not None and hasattr(self, "_auto_switch"):
            self._auto_switch.set_active(False)

        if auto_was_active or getattr(self, "_systemd_was_active", False):
            from pathlib import Path
            import subprocess
            svc_file = Path.home() / ".config/systemd/user/g502-profile-manager.service"
            if svc_file.exists():
                try:
                    subprocess.run(["systemctl", "--user", "start", "g502-profile-manager.service"], check=False)
                except Exception:
                    pass

        if hasattr(self, "_tray") and self._tray:
            self._tray.destroy()
        return False
