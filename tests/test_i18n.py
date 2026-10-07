"""
Pruebas unitarias para el módulo de Internacionalización (i18n).
"""

import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

src_path = Path(__file__).resolve().parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

import i18n
from i18n import (
    I18nManager,
    _,
    get_available_languages,
    get_language,
    gettext,
    register_language_change_callback,
    set_language,
    set_preferences_file,
    unregister_language_change_callback,
)


class TestI18n(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.pref_file = Path(self.temp_dir) / "test-preferences.json"
        # Configurar archivo temporal para no interferir con las preferencias del usuario
        set_preferences_file(self.pref_file)
        set_language("es", persist=False)

    def tearDown(self):
        # Restaurar configuración predeterminada
        set_preferences_file(i18n.DEFAULT_PREFERENCES_FILE)
        set_language("es", persist=False)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_default_language_is_spanish(self):
        self.assertEqual(get_language(), "es")
        self.assertEqual(_("Aplicar al Ratón"), "Aplicar al Ratón")
        self.assertEqual(_("Guardar"), "Guardar")

    def test_translation_to_english(self):
        set_language("en", persist=False)
        self.assertEqual(get_language(), "en")
        self.assertEqual(_("Aplicar al Ratón"), "Apply to Mouse")
        self.assertEqual(_("Guardar"), "Save")
        self.assertEqual(_("Auto-Perfil"), "Auto-Profile")
        self.assertEqual(_("Buscando mouse..."), "Searching for mouse...")
        self.assertEqual(_("Sensibilidad DPI"), "DPI Sensitivity")
        self.assertEqual(_("Iluminación LED"), "LED Lighting")
        self.assertEqual(_("Dar Feedback / Reportar"), "Give Feedback / Report")

    def test_untranslated_key_returns_original(self):
        set_language("en", persist=False)
        unknown = "Texto sin traducción alguna"
        self.assertEqual(_(unknown), unknown)
        self.assertEqual(gettext(unknown), unknown)

    def test_invalid_language_falls_back_to_default(self):
        set_language("fr", persist=False)
        self.assertEqual(get_language(), "es")
        self.assertEqual(_("Guardar"), "Guardar")

    def test_available_languages_catalog(self):
        langs = get_available_languages()
        self.assertIn("es", langs)
        self.assertIn("en", langs)
        self.assertEqual(langs["es"], "Español")
        self.assertEqual(langs["en"], "English")

    def test_persistence_atomic_write_and_reload(self):
        # Guardar en inglés
        set_language("en", persist=True)
        self.assertTrue(self.pref_file.exists())

        with open(self.pref_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data.get("language"), "en")

        # Crear una nueva instancia independiente y verificar que cargue "en"
        new_manager = I18nManager(preferences_file=self.pref_file)
        self.assertEqual(new_manager.get_language(), "en")
        self.assertEqual(new_manager.translate("Guardar"), "Save")

    def test_language_change_callbacks(self):
        notified = []

        def callback(new_lang):
            notified.append(new_lang)

        register_language_change_callback(callback)
        try:
            set_language("en", persist=False)
            self.assertEqual(notified, ["en"])

            set_language("es", persist=False)
            self.assertEqual(notified, ["en", "es"])
        finally:
            unregister_language_change_callback(callback)

        # Después de desregistrar, no debe recibir más notificaciones
        set_language("en", persist=False)
        self.assertEqual(notified, ["en", "es"])




    def test_lighting_and_feedback_translations(self):
        set_language("en", persist=False)
        self.assertEqual(_("Colores Calibrados G502:"), "Calibrated G502 Colors:")
        self.assertEqual(_("Selector de color interactivo"), "Interactive color picker")
        self.assertEqual(_("1s (Rápido)"), "1s (Fast)")
        self.assertEqual(_("2s (Normal)"), "2s (Normal)")
        self.assertEqual(_("3s (Suave)"), "3s (Smooth)")
        self.assertEqual(_("5s (Lento)"), "5s (Slow)")
        self.assertEqual(_("10s (Relax)"), "10s (Relax)")
        self.assertEqual(
            _("Personaliza el modo, color y efectos del logotipo G e indicadores DPI ({zones} zonas)").format(zones=2),
            "Customize mode, color and effects of the G logo and DPI indicators (2 zones)"
        )
        self.assertEqual(
            _("Soporte experimental para {short_name}: Ayúdanos a calibrarlo reportando cualquier anomalía.").format(short_name="G502 X"),
            "Experimental support for G502 X: Help us calibrate it by reporting any issues."
        )
        self.assertEqual(_("Ayúdanos a Mejorar y Calibrar tu Ratón"), "Help Us Improve and Calibrate Your Mouse")
        self.assertEqual(_("💬 Abrir en Reddit"), "💬 Open in Reddit")

    def test_detect_system_language(self):
        from unittest.mock import patch
        import os

        # Caso Español
        with patch.dict(os.environ, {"LANG": "es_CO.UTF-8", "LC_ALL": "", "LC_MESSAGES": ""}):
            self.assertEqual(i18n.detect_system_language(), "es")

        with patch.dict(os.environ, {"LANG": "es_ES.UTF-8", "LC_ALL": "", "LC_MESSAGES": ""}):
            self.assertEqual(i18n.detect_system_language(), "es")

        # Caso Inglés
        with patch.dict(os.environ, {"LANG": "en_US.UTF-8", "LC_ALL": "", "LC_MESSAGES": ""}):
            self.assertEqual(i18n.detect_system_language(), "en")

        # Caso Internacional (ej. Francés, Alemán) -> fallback inglés
        with patch.dict(os.environ, {"LANG": "fr_FR.UTF-8", "LC_ALL": "", "LC_MESSAGES": ""}):
            self.assertEqual(i18n.detect_system_language(), "en")

    def test_first_run_auto_detection_and_creation(self):
        from unittest.mock import patch
        import os

        # Si el archivo de preferencias no existe y el sistema está en inglés,
        # debe autodetectar "en" y persistirlo
        test_pref = Path(self.temp_dir) / "first_run_pref.json"
        self.assertFalse(test_pref.exists())

        with patch.dict(os.environ, {"LANG": "en_GB.UTF-8", "LC_ALL": "", "LC_MESSAGES": ""}):
            manager = I18nManager(preferences_file=test_pref)
            self.assertEqual(manager.get_language(), "en")
            self.assertTrue(test_pref.exists())
            with open(test_pref, "r", encoding="utf-8") as f:
                saved = json.load(f)
            self.assertEqual(saved.get("language"), "en")

    def test_cli_status_i18n_formatting(self):
        import io
        from unittest.mock import MagicMock, patch
        from cli import cmd_status

        mock_repo = MagicMock()
        mock_repo.list_all.return_value = []
        mock_adapter = MagicMock()
        mock_adapter.find_device.return_value = None

        with patch("cli.get_services", return_value=(mock_repo, MagicMock(), MagicMock(), mock_adapter, MagicMock())):
            # En Español
            set_language("es", persist=False)
            out_es = io.StringIO()
            with patch("sys.stdout", out_es):
                cmd_status(MagicMock())
            self.assertIn("G502 Profile Manager - Estado", out_es.getvalue())
            self.assertIn("Ningún ratón G502 detectado", out_es.getvalue())

            # En Inglés
            set_language("en", persist=False)
            out_en = io.StringIO()
            with patch("sys.stdout", out_en):
                cmd_status(MagicMock())
            self.assertIn("G502 Profile Manager - Status", out_en.getvalue())
            self.assertIn("No G502 mouse detected", out_en.getvalue())

if __name__ == "__main__":
    unittest.main()
