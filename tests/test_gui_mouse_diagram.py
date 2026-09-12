"""
Pruebas unitarias para el componente de esquema visual del ratón G502 (G502MouseDiagram).
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

import cairo
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from domain import Action, Button, Profile
from gui.mouse_diagram import BUTTON_METADATA, G502MouseDiagram


class TestG502MouseDiagram(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Adw.init()

    def setUp(self):
        self.clicked_button = None

        def on_click(btn_id, btn_name):
            self.clicked_button = (btn_id, btn_name)

        self.diagram = G502MouseDiagram(on_button_clicked=on_click)

    def test_diagram_initial_properties(self):
        self.assertIsNotNone(self.diagram)
        self.assertEqual(self.diagram.get_content_width(), 440)
        self.assertEqual(self.diagram.get_content_height(), 580)
        # 11 botones soportados
        self.assertEqual(len(BUTTON_METADATA), 11)
        self.assertIn("G5", BUTTON_METADATA)
        self.assertIn("G4", BUTTON_METADATA)
        self.assertIn("SNIPER", BUTTON_METADATA)
        self.assertIn("G7", BUTTON_METADATA)
        self.assertIn("G8", BUTTON_METADATA)
        self.assertIn("G9", BUTTON_METADATA)

    def test_set_led_color(self):
        self.diagram.set_led_color("#00E5FF")
        r, g, b = self.diagram._led_color_rgb
        self.assertAlmostEqual(r, 0.0, places=2)
        self.assertAlmostEqual(g, 0.898, places=2)
        self.assertAlmostEqual(b, 1.0, places=2)

    def test_highlight_button(self):
        self.diagram.highlight_button("G5")
        self.assertEqual(self.diagram._hovered_button, "G5")

        self.diagram.highlight_button(None)
        self.assertIsNone(self.diagram._hovered_button)

    def test_set_profile(self):
        profile = Profile(
            name="Warframe Live",
            application_id="steam:230410",
            dpi=8000,
            led_color="#00E5FF",
        )
        action_h1 = Action("wf_ability_1", "Habilidad 1", "steam:230410", "Habilidad 1", "key", "1")
        profile.assign(Button(button_id="G5", name="Botón G5"), action_h1)

        self.diagram.set_profile(profile)
        self.assertEqual(self.diagram._current_profile, profile)
        self.assertAlmostEqual(self.diagram._led_color_rgb[2], 1.0, places=2)

    def test_draw_func_execution(self):
        # Crear superficie Cairo en memoria para verificar que el método de dibujo no arroja errores
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 440, 580)
        cr = cairo.Context(surface)

        profile = Profile(
            name="Test",
            application_id="steam:230410",
            dpi=8000,
            led_color="#00E5FF",
        )
        self.diagram.set_profile(profile)
        self.diagram._draw_func(self.diagram, cr, 440, 580)

        # Verificar que se hayan registrado las áreas clicables para los botones
        self.assertGreaterEqual(len(self.diagram._hit_targets), 8)
        self.assertIn("G5", self.diagram._hit_targets)
        self.assertIn("SNIPER", self.diagram._hit_targets)

        # Probar detección de colisión
        g5_box = self.diagram._hit_targets["G5"]
        mid_x = (g5_box[0] + g5_box[2]) / 2.0
        mid_y = (g5_box[1] + g5_box[3]) / 2.0

        hit_btn = self.diagram._find_hit_button(mid_x, mid_y)
        self.assertEqual(hit_btn, "G5")

        # Probar clic
        self.diagram._on_click_pressed(None, 1, mid_x, mid_y)
        self.assertIsNotNone(self.clicked_button)
        self.assertEqual(self.clicked_button[0], "G5")


if __name__ == "__main__":
    unittest.main()
