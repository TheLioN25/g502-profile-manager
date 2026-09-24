"""
Pruebas unitarias para la lógica de la interfaz gráfica GTK4 / Libadwaita.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

src_path = Path(__file__).resolve().parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from domain import Action, Application, Button, Profile
from gui.app import G502Application
from gui.dialogs import ActionPickerDialog, NewProfileDialog
from gui.window import MainWindow, BUTTON_DEFINITIONS
from services.action_catalog import ActionCatalogService
from services.profile_manager import ProfileManager
from storage.profile_repository import JsonProfileRepository


class TestGuiLogic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Inicializar Adw para entorno de pruebas
        Adw.init()

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.profiles_path = Path(self.temp_dir.name) / "profiles.json"
        self.repo = JsonProfileRepository(self.profiles_path)
        self.profile_manager = ProfileManager(self.repo)
        self.catalog_service = ActionCatalogService()

        # Mock discovery adapter
        self.mock_discovery = MagicMock()
        self.mock_discovery.discover_all_applications.return_value = [
            Application(application_id="steam:230410", name="Warframe"),
            Application(application_id="steam:1284210", name="Guild Wars 2"),
        ]

        # Mock ratbag adapter
        self.mock_ratbag = MagicMock()
        self.mock_ratbag.find_device.return_value = "warbling-mara"
        self.mock_ratbag.apply_profile.return_value = True

        self.app = G502Application()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_application_instantiation(self):
        self.assertEqual(self.app.get_application_id(), "io.github.thelion.G502ProfileManager")

    def test_main_window_initialization(self):
        window = MainWindow(
            app=self.app,
            profile_manager=self.profile_manager,
            catalog_service=self.catalog_service,
            discovery_adapter=self.mock_discovery,
            ratbag_adapter=self.mock_ratbag,
        )

        self.assertIsNotNone(window)
        self.assertEqual(window.get_title(), "G502 Profile Manager")
        self.assertEqual(len(window._app_rows), 2)
        # Verifica que los botones del G502 estén mapeados
        self.assertIn("G5", window._button_rows)
        self.assertIn("G4", window._button_rows)
        self.assertIn("SNIPER", window._button_rows)
        self.assertIn("G7", window._button_rows)
        self.assertIn("G8", window._button_rows)

    def test_main_window_select_application_and_save(self):
        window = MainWindow(
            app=self.app,
            profile_manager=self.profile_manager,
            catalog_service=self.catalog_service,
            discovery_adapter=self.mock_discovery,
            ratbag_adapter=self.mock_ratbag,
        )

        app_warframe = Application(application_id="steam:230410", name="Warframe")
        window._select_application(app_warframe)

        self.assertEqual(window._selected_app.application_id, "steam:230410")
        self.assertIsNotNone(window._current_profile)

        # Modificar DPI y color
        window._dpi_adjustment.set_value(8000)
        window._color_hex_entry.set_text("#00E5FF")

        # Asignar acción a G5
        action_h1 = Action(
            action_id="wf_ability_1",
            name="Habilidad 1",
            application_id="steam:230410",
            description="Primera habilidad",
            binding_type="key",
            binding_value="1",
        )
        window._current_profile.assign(Button(button_id="G5", name="Botón G5"), action_h1)

        # Simular clic en Guardar
        window._on_save_profile_clicked(None)

        saved = self.profile_manager.get_active_profile_for_application("steam:230410")
        self.assertIsNotNone(saved)
        self.assertEqual(saved.dpi.dpi, 8000)
        self.assertEqual(saved.led_color, "#00E5FF")
        assignment = saved.get_assignment_for_button("G5")
        self.assertIsNotNone(assignment)
        self.assertEqual(assignment.action.action_id, "wf_ability_1")

    def test_main_window_apply_to_mouse(self):
        window = MainWindow(
            app=self.app,
            profile_manager=self.profile_manager,
            catalog_service=self.catalog_service,
            discovery_adapter=self.mock_discovery,
            ratbag_adapter=self.mock_ratbag,
        )

        app_warframe = Application(application_id="steam:230410", name="Warframe")
        window._select_application(app_warframe)

        with patch("threading.Thread") as mock_thread_cls:
            mock_thread_cls.side_effect = lambda target, daemon: MagicMock(start=target)
            window._on_apply_to_mouse_clicked(None)

        self.mock_ratbag.find_device.assert_called()
        self.mock_ratbag.apply_profile.assert_called_once_with("warbling-mara", window._current_profile)

    def test_action_picker_dialog(self):
        parent_window = Gtk.Window()
        categories = {
            "Combate": [
                Action("act_melee", "Ataque Melee", "steam:230410", "Golpe rápido", "key", "e", "Combate")
            ]
        }

        selected_action = None

        def callback(action):
            nonlocal selected_action
            selected_action = action

        dialog = ActionPickerDialog(
            parent_window=parent_window,
            button_id="SNIPER",
            button_name="Botón SNIPER",
            app_id="steam:230410",
            app_name="Warframe",
            categories=categories,
            current_action=None,
            on_action_selected=callback,
        )

        self.assertIsNotNone(dialog)
        self.assertEqual(len(dialog._rows), 1)

        # Probar selección de acción
        handler = dialog._make_select_handler(categories["Combate"][0])
        handler()
        self.assertEqual(selected_action.action_id, "act_melee")

        # Probar limpieza de asignación
        dialog._on_clear_clicked(None)
        self.assertIsNone(selected_action)

    def test_new_profile_dialog(self):
        parent_window = Gtk.Window()
        created_name = None

        def callback(name: str):
            nonlocal created_name
            created_name = name

        dialog = NewProfileDialog(
            parent_window=parent_window,
            app_name="Warframe",
            on_profile_created=callback,
        )
        self.assertIsNotNone(dialog)

        # Simular cambio de texto y clic en Crear
        dialog._entry_row.set_text("Warframe Eidolon Hunt")
        dialog._on_create_clicked(None)
        self.assertEqual(created_name, "Warframe Eidolon Hunt")

    def test_main_window_multi_profile_dropdown_and_switching(self):
        # Crear 2 perfiles iniciales para Warframe
        p1 = self.profile_manager.create_profile("DPS Saryn", "steam:230410", 1200)
        p2 = self.profile_manager.create_profile("Volt Speed", "steam:230410", 2400)

        window = MainWindow(
            app=self.app,
            profile_manager=self.profile_manager,
            catalog_service=self.catalog_service,
            discovery_adapter=self.mock_discovery,
            ratbag_adapter=self.mock_ratbag,
        )

        app_warframe = Application(application_id="steam:230410", name="Warframe")
        window._select_application(app_warframe)

        self.assertEqual(len(window._current_app_profiles), 2)
        self.assertEqual(window._current_profile.id, p1.id)

        # Simular cambio de selección en el dropdown a Volt Speed (índice 1)
        window._profile_dropdown.set_selected(1)
        self.assertEqual(window._current_profile.id, p2.id)
        self.assertEqual(window._current_profile.dpi.dpi, 2400)

    def test_main_window_duplicate_and_set_default_and_delete(self):
        p1 = self.profile_manager.create_profile("Warframe Main", "steam:230410", 1600)

        window = MainWindow(
            app=self.app,
            profile_manager=self.profile_manager,
            catalog_service=self.catalog_service,
            discovery_adapter=self.mock_discovery,
            ratbag_adapter=self.mock_ratbag,
        )

        app_warframe = Application(application_id="steam:230410", name="Warframe")
        window._select_application(app_warframe)

        # 1. Duplicar perfil
        window._on_duplicate_profile_clicked(None)
        self.assertEqual(len(window._current_app_profiles), 2)
        duplicated = window._current_profile
        self.assertIn("(Copia)", duplicated.name)

        # 2. Marcar como predeterminado
        window._on_set_default_profile_clicked(None)
        default_p = self.profile_manager.get_default_profile("steam:230410")
        self.assertEqual(default_p.id, duplicated.id)

        # 3. Eliminar perfil duplicado
        window._on_delete_profile_clicked(None)
        self.assertEqual(len(window._current_app_profiles), 1)
        self.assertEqual(window._current_profile.id, p1.id)

        # 4. Intentar eliminar el único perfil no debe eliminarlo
        window._on_delete_profile_clicked(None)
        self.assertEqual(len(window._current_app_profiles), 1)

    def test_main_window_configured_and_unconfigured_separation_and_search(self):
        # Crear perfil solo para Warframe
        self.profile_manager.create_profile("Warframe Main", "steam:230410", 1600)

        window = MainWindow(
            app=self.app,
            profile_manager=self.profile_manager,
            catalog_service=self.catalog_service,
            discovery_adapter=self.mock_discovery,
            ratbag_adapter=self.mock_ratbag,
        )

        # Warframe debe estar en _configured_rows y Guild Wars 2 en _unconfigured_rows
        conf_ids = [app.application_id for _, app in window._configured_rows]
        unconf_ids = [app.application_id for _, app in window._unconfigured_rows]
        self.assertIn("steam:230410", conf_ids)
        self.assertIn("steam:1284210", unconf_ids)

        # Probar búsqueda en no configuradas
        window._app_search_entry.set_text("Guild")
        window._on_app_search_changed(window._app_search_entry)
        for row, app in window._unconfigured_rows:
            if app.application_id == "steam:1284210":
                self.assertTrue(row.get_visible())

        window._app_search_entry.set_text("ZzzNonExistent")
        window._on_app_search_changed(window._app_search_entry)
        for row, app in window._unconfigured_rows:
            if app.application_id == "steam:1284210":
                self.assertFalse(row.get_visible())

    def test_main_window_auto_detection_switch_and_lifecycle(self):
        mock_engine = MagicMock()

        window = MainWindow(
            app=self.app,
            profile_manager=self.profile_manager,
            catalog_service=self.catalog_service,
            discovery_adapter=self.mock_discovery,
            ratbag_adapter=self.mock_ratbag,
            automation_engine=mock_engine,
        )

        self.assertIsNotNone(window._auto_switch)
        self.assertFalse(window._auto_switch.get_active())

        # 1. Activar el interruptor
        window._auto_switch.set_active(True)
        self.assertTrue(window._auto_switch.get_active())
        self.assertIsNotNone(window._auto_thread)

        # Probar callback de perfil aplicado
        test_prof = Profile(name="Saryn Test", application_id="steam:230410", dpi=1600, profile_id="p1")
        window._on_auto_profile_applied("Warframe", test_prof)
        self.assertIn("Warframe", window._window_title.get_subtitle())
        self.assertIn("1600 DPI", window._window_title.get_subtitle())

        # Probar callback de escritorio restaurado
        window._on_auto_desktop_restored()
        self.assertIn("steam:230410", window._window_title.get_subtitle())

        # 2. Desactivar el interruptor
        window._auto_switch.set_active(False)
        self.assertFalse(window._auto_switch.get_active())
        mock_engine.stop.assert_called()

        # 3. Probar _on_close_request cuando estaba activo
        mock_engine.reset_mock()
        window._auto_switch.set_active(True)
        window._on_close_request(window)
        self.assertFalse(window._auto_switch.get_active())
        mock_engine.stop.assert_called()

    def test_main_window_select_application_by_id(self):
        p_wf = self.profile_manager.create_profile("Warframe Main", "steam:230410", 1200)
        p_gw2 = self.profile_manager.create_profile("GW2 WvW", "steam:1284210", 2000)

        window = MainWindow(
            app=self.app,
            profile_manager=self.profile_manager,
            catalog_service=self.catalog_service,
            discovery_adapter=self.mock_discovery,
            ratbag_adapter=self.mock_ratbag,
        )

        # Inicialmente está en Warframe (primera configurada)
        self.assertEqual(window._selected_app.application_id, "steam:230410")
        self.assertEqual(window._current_profile.id, p_wf.id)

        # Seleccionar Guild Wars 2 mediante su ID y cargar su perfil específico
        res = window.select_application_by_id("steam:1284210", profile_id=p_gw2.id)
        self.assertTrue(res)
        self.assertEqual(window._selected_app.application_id, "steam:1284210")
        self.assertEqual(window._current_profile.id, p_gw2.id)
        self.assertEqual(window._current_profile.dpi.dpi, 2000)
        self.assertEqual(window._dpi_display_label.get_text(), "2000 DPI")

        # Intentar seleccionar un ID inexistente debe devolver False
        res_non = window.select_application_by_id("non_existent_app")
        self.assertFalse(res_non)


if __name__ == "__main__":
    unittest.main()
