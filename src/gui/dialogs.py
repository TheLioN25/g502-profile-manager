"""
Diálogos modales para la interfaz gráfica G502 Profile Manager.
"""

from __future__ import annotations

from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from domain import Action
from i18n import _


class ActionPickerDialog(Adw.Window):
    """
    Diálogo modal para seleccionar una acción del catálogo o asignar una tecla personalizada
    a un botón específico del ratón G502 HERO.
    """

    def __init__(
        self,
        parent_window: Gtk.Window,
        button_id: str,
        button_name: str,
        app_id: str,
        app_name: str,
        categories: dict[str, list[Action]],
        current_action: Action | None,
        on_action_selected: Callable[[Action | None], None],
    ):
        super().__init__(
            title=f"{_('Asignar')} {_('button_name') if button_name in () else _(button_name)}",
            transient_for=parent_window,
            modal=True,
            default_width=460,
            default_height=560,
        )

        self._button_id = button_id
        self._button_name = button_name
        self._app_id = app_id
        self._categories = categories
        self._on_action_selected = on_action_selected

        # Contenedor principal
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(main_box)

        # HeaderBar
        header = Adw.HeaderBar()
        title_widget = Adw.WindowTitle(
            title=_(button_name),
            subtitle=f"{_('Catálogo de')} {app_name}",
        )
        header.set_title_widget(title_widget)

        # Botón Desasignar en la cabecera
        clear_btn = Gtk.Button(label=_("Quitar Asignación"))
        clear_btn.add_css_class("destructive-action")
        clear_btn.connect("clicked", self._on_clear_clicked)
        header.pack_start(clear_btn)

        main_box.append(header)

        # Buscador de acciones
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        search_box.set_margin_start(16)
        search_box.set_margin_end(16)
        search_box.set_margin_top(12)
        search_box.set_margin_bottom(8)

        self._search_entry = Gtk.SearchEntry(placeholder_text=_("Buscar acción o habilidad..."))
        self._search_entry.set_hexpand(True)
        self._search_entry.connect("search-changed", self._on_search_changed)
        search_box.append(self._search_entry)
        main_box.append(search_box)

        # ScrolledWindow con las acciones
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        main_box.append(scrolled)

        # Página de preferencias con grupos por categoría
        self._pref_page = Adw.PreferencesPage()
        scrolled.set_child(self._pref_page)

        self._rows: list[tuple[Adw.ActionRow, Action]] = []
        self._build_action_categories()

        # Grupo inferior: Asignación personalizada
        custom_group = Adw.PreferencesGroup(
            title=_("Asignación Personalizada"),
            description=_("Asigna directamente cualquier tecla del teclado"),
        )
        custom_row = Adw.ActionRow(title=_("Tecla o atajo"))
        self._custom_key_entry = Gtk.Entry(placeholder_text=_("ej: e, 1, space, leftctrl"))
        self._custom_key_entry.set_valign(Gtk.Align.CENTER)
        self._custom_key_entry.connect("activate", self._on_custom_key_applied)

        apply_custom_btn = Gtk.Button(label=_("Asignar"))
        apply_custom_btn.set_valign(Gtk.Align.CENTER)
        apply_custom_btn.add_css_class("suggested-action")
        apply_custom_btn.connect("clicked", self._on_custom_key_applied)

        custom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        custom_box.append(self._custom_key_entry)
        custom_box.append(apply_custom_btn)
        custom_row.add_suffix(custom_box)
        custom_group.add(custom_row)
        self._pref_page.add(custom_group)

    def _build_action_categories(self):
        icon_map = {
            "Combate": "⚔️",
            "Armas": "🗡️",
            "Habilidades": "⚡",
            "Profesión": "🔮",
            "Apoyo y Élite": "🛡️",
            "Movimiento": "🏃",
            "Interacción": "🖐️",
            "Navegación": "🌐",
            "Edición": "✏️",
            "Multimedia": "🔊",
        }

        for cat_name, actions in self._categories.items():
            if not actions:
                continue

            icon = icon_map.get(cat_name, "📁")
            group = Adw.PreferencesGroup(title=f"{icon} {_(cat_name)}")
            self._pref_page.add(group)

            for action in actions:
                sub_text = _(action.description) if action.description else f"{_('Comando:')} {action.binding_type} [{action.binding_value}]"
                row = Adw.ActionRow(
                    title=_(action.name),
                    subtitle=sub_text,
                )
                row.set_activatable(True)

                # Chip que muestra la tecla/comando
                badge = Gtk.Label(label=f"[{action.binding_value}]")
                badge.add_css_class("action-chip")
                badge.set_valign(Gtk.Align.CENTER)
                row.add_suffix(badge)

                # Botón de asignación directa
                select_btn = Gtk.Button(label=_("Asignar"))
                select_btn.set_valign(Gtk.Align.CENTER)
                select_btn.add_css_class("suggested-action")
                select_btn.connect("clicked", self._make_select_handler(action))
                row.add_suffix(select_btn)

                # Permitir hacer clic en toda la fila para asignar
                row.connect("activated", self._make_select_handler(action))

                group.add(row)
                self._rows.append((row, action))

    def _make_select_handler(self, action: Action):
        def handler(*_args):
            self._on_action_selected(action)
            self.close()

        return handler

    def _on_clear_clicked(self, _btn):
        self._on_action_selected(None)
        self.close()

    def _on_custom_key_applied(self, _widget):
        text = self._custom_key_entry.get_text().strip()
        if not text:
            return

        action = Action(
            action_id=f"custom_{text.casefold()}",
            name=f"{_('Tecla')} {text.upper()}",
            application_id=self._app_id,
            description=_("Tecla asignada manualmente"),
            binding_type="key",
            binding_value=text,
            category="Personalizado",
        )
        self._on_action_selected(action)
        self.close()

    def _on_search_changed(self, entry: Gtk.SearchEntry):
        query = entry.get_text().strip().casefold()
        for row, action in self._rows:
            if not query:
                row.set_visible(True)
            else:
                matches = (
                    query in action.name.casefold()
                    or query in _(action.name).casefold()
                    or query in action.binding_value.casefold()
                    or query in (action.description or "").casefold()
                    or query in _(action.description or "").casefold()
                )
                row.set_visible(matches)


class NewProfileDialog(Adw.Window):
    """
    Diálogo modal para crear un nuevo perfil con un nombre personalizado.
    """

    def __init__(
        self,
        parent_window: Gtk.Window,
        app_name: str,
        on_profile_created: Callable[[str], None],
    ):
        super().__init__(
            title=_("Nuevo Perfil"),
            transient_for=parent_window,
            modal=True,
            default_width=380,
            default_height=200,
        )
        self._on_profile_created = on_profile_created

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(main_box)

        header = Adw.HeaderBar()
        title_widget = Adw.WindowTitle(title=_("Crear Nuevo Perfil"), subtitle=app_name)
        header.set_title_widget(title_widget)

        cancel_btn = Gtk.Button(label=_("Cancelar"))
        cancel_btn.connect("clicked", lambda _: self.close())
        header.pack_start(cancel_btn)

        create_btn = Gtk.Button(label=_("Crear"))
        create_btn.add_css_class("suggested-action")
        create_btn.connect("clicked", self._on_create_clicked)
        header.pack_end(create_btn)

        main_box.append(header)

        # Formulario
        pref_page = Adw.PreferencesPage()
        pref_group = Adw.PreferencesGroup(
            title=_("Detalles del Perfil"),
            description=_("Ingresa un nombre descriptivo para esta configuración."),
        )
        pref_page.add(pref_group)

        self._entry_row = Adw.EntryRow(title=_("Nombre del Perfil"))
        self._entry_row.set_text(f"{app_name} {_('Alternativo')}")
        self._entry_row.connect("entry-activated", lambda _: self._on_create_clicked(None))
        pref_group.add(self._entry_row)

        main_box.append(pref_page)

    def _on_create_clicked(self, _btn):
        name = self._entry_row.get_text().strip()
        if not name:
            return
        self.close()
        self._on_profile_created(name)
