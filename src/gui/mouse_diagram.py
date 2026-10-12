"""
Componente visual e interactivo del ratón Logitech G502 (GTK4 + Cairo).
Remasterización vectorial de alta fidelidad con sombreado 3D, retroiluminación reactiva,
acabados en ciber-blueprint y líneas guía ortogonales con bisel técnico a 45 grados.
"""

from __future__ import annotations

import math
from typing import Callable

import cairo
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, Gtk

from domain import Profile
from i18n import _


BUTTON_METADATA: dict[str, dict[str, str | int]] = {
    "LEFT": {"name": "Clic Izquierdo", "side": "left_top"},
    "RIGHT": {"name": "Clic Derecho", "side": "right_top"},
    "MIDDLE": {"name": "Clic Rueda", "side": "center_wheel"},
    "WHEEL_LEFT": {"name": "Rueda Izq.", "side": "wheel_tilt_l"},
    "WHEEL_RIGHT": {"name": "Rueda Der.", "side": "wheel_tilt_r"},
    "G8": {"name": "Botón G8 (DPI Up)", "side": "left"},
    "G7": {"name": "Botón G7 (DPI Down)", "side": "left"},
    "G5": {"name": "Botón G5 (Delantero)", "side": "left"},
    "G4": {"name": "Botón G4 (Trasero)", "side": "left"},
    "SNIPER": {"name": "Botón SNIPER", "side": "left"},
    "G9": {"name": "Botón G9 (Perfil)", "side": "right"},
}


class G502MouseDiagram(Gtk.DrawingArea):
    """
    Área de dibujo vectorial interactiva que representa la silueta ergonómica del ratón Logitech G502.
    Muestra los botones físicos, líneas guía técnicas y tarjetas HUD con acciones asignadas.
    Permite hacer clic sobre cualquier botón o tarjeta para abrir el diálogo de configuración.
    """

    def __init__(self, on_button_clicked: Callable[[str, str], None] | None = None):
        super().__init__()
        self.set_content_width(440)
        self.set_content_height(580)
        self.set_hexpand(False)
        self.set_vexpand(True)

        self._on_button_clicked = on_button_clicked
        self._current_profile: Profile | None = None
        self._hovered_button: str | None = None
        self._led_color_rgb: tuple[float, float, float] = (0.0, 0.898, 1.0)  # #00E5FF por defecto

        # Diccionario dinámico de áreas clicables {(btn_id): (x1, y1, x2, y2)}
        self._hit_targets: dict[str, tuple[float, float, float, float]] = {}

        self.set_draw_func(self._draw_func)

        # Controlador de movimiento para hover
        motion = Gtk.EventControllerMotion()
        motion.connect("motion", self._on_motion)
        motion.connect("leave", self._on_leave)
        self.add_controller(motion)

        # Gesto de clic
        click = Gtk.GestureClick()
        click.connect("pressed", self._on_click_pressed)
        self.add_controller(click)

    def set_profile(self, profile: Profile | None):
        """Actualiza las asignaciones y color LED a partir del perfil."""
        self._current_profile = profile
        if profile and profile.led_color:
            self.set_led_color(profile.led_color)
        else:
            self.queue_draw()

    def set_led_color(self, hex_code: str):
        """Actualiza el color del logotipo G y acentos LED."""
        clean = hex_code.lstrip("#")
        if len(clean) == 6:
            try:
                r = int(clean[0:2], 16) / 255.0
                g = int(clean[2:4], 16) / 255.0
                b = int(clean[4:6], 16) / 255.0
                self._led_color_rgb = (r, g, b)
            except ValueError:
                pass
        self.queue_draw()

    def highlight_button(self, button_id: str | None):
        """Resalta externamente un botón (por ejemplo al posarse sobre una fila)."""
        if self._hovered_button != button_id:
            self._hovered_button = button_id
            self.queue_draw()

    # -------------------------------------------------------------------------
    # Renderizado con Cairo
    # -------------------------------------------------------------------------
    def _draw_func(self, _area, cr: cairo.Context, width: int, height: int):
        self._hit_targets.clear()

        # Fondo estilizado con viñeta radial oscura
        bg = cairo.RadialGradient(width * 0.5, height * 0.5, 60, width * 0.5, height * 0.5, max(width, height) * 0.7)
        bg.add_color_stop_rgb(0.0, 0.08, 0.09, 0.12)
        bg.add_color_stop_rgb(0.7, 0.04, 0.05, 0.07)
        bg.add_color_stop_rgb(1.0, 0.02, 0.03, 0.04)
        cr.set_source(bg)
        cr.paint()

        # Cuadrícula sutil de precisión estilo CAD / Blueprint
        cr.set_line_width(0.5)
        cr.set_source_rgba(0.25, 0.45, 0.65, 0.06)
        for x in range(0, width, 24):
            cr.move_to(x, 0)
            cr.line_to(x, height)
            cr.stroke()
        for y in range(0, height, 24):
            cr.move_to(0, y)
            cr.line_to(width, y)
            cr.stroke()

        # Corchetes técnicos de encuadre en las esquinas
        cr.set_line_width(1.2)
        cr.set_source_rgba(0.0, 0.898, 1.0, 0.35)
        bracket_pad = 18
        bracket_len = 16
        for cx_c, cy_c, dx, dy in [
            (bracket_pad, bracket_pad, 1, 1),
            (width - bracket_pad, bracket_pad, -1, 1),
            (bracket_pad, height - bracket_pad, 1, -1),
            (width - bracket_pad, height - bracket_pad, -1, -1),
        ]:
            cr.move_to(cx_c + dx * bracket_len, cy_c)
            cr.line_to(cx_c, cy_c)
            cr.line_to(cx_c, cy_c + dy * bracket_len)
            cr.stroke()

        # Centro y escala uniforme del ratón en la vista
        cx = width * 0.50
        cy = height * 0.50
        natural_w = 400.0
        natural_h = 430.0
        scale = min(width / natural_w, height / natural_h) * 0.85
        scale = max(0.60, min(scale, 2.5))

        cr.save()
        cr.translate(cx, cy)
        cr.scale(scale, scale)

        # 1. Silueta principal y chasis multicapa del ratón
        self._draw_mouse_body(cr)

        # 2. Mecanismos interiores: Rueda 3D, iluminaciones LED y lomo
        self._draw_mouse_details(cr)

        # 3. Puntos de anclaje, líneas biseladas a 45° y tarjetas HUD
        self._draw_buttons_and_callouts(cr, cx, cy, scale)

        cr.restore()

    def _draw_round_rect(self, cr: cairo.Context, x: float, y: float, w: float, h: float, r: float):
        """Dibuja un rectángulo con esquinas redondeadas en el contexto actual."""
        cr.new_sub_path()
        cr.arc(x + w - r, y + r, r, -0.5 * math.pi, 0)
        cr.arc(x + w - r, y + h - r, r, 0, 0.5 * math.pi)
        cr.arc(x + r, y + h - r, r, 0.5 * math.pi, math.pi)
        cr.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
        cr.close_path()

    def _mouse_outline_path(self, cr: cairo.Context, off_x: float = 0, off_y: float = 0):
        """Genera el contorno ergonómico icónico del cuerpo del ratón."""
        cr.new_sub_path()
        cr.move_to(off_x + 0, off_y - 188)
        # Clic derecho borde y punta angular
        cr.line_to(off_x + 48, off_y - 182)
        cr.line_to(off_x + 68, off_y - 156)
        # Flanco derecho ergonómico
        cr.curve_to(off_x + 75, off_y - 100, off_x + 78, off_y - 30, off_x + 76, off_y + 30)
        cr.curve_to(off_x + 74, off_y + 80, off_x + 68, off_y + 125, off_x + 58, off_y + 155)
        # Curvatura trasera del lomo
        cr.curve_to(off_x + 44, off_y + 185, off_x + 24, off_y + 188, off_x + 0, off_y + 188)
        cr.curve_to(off_x - 24, off_y + 188, off_x - 44, off_y + 185, off_x - 58, off_y + 155)
        # Borde trasero izquierdo hacia el apoyo del pulgar
        cr.curve_to(off_x - 68, off_y + 125, off_x - 66, off_y + 98, off_x - 68, off_y + 88)
        # Aleta de apoyo para el pulgar (Thumb Wing)
        cr.curve_to(off_x - 96, off_y + 78, off_x - 110, off_y + 38, off_x - 104, off_y + 5)
        cr.curve_to(off_x - 96, off_y - 22, off_x - 74, off_y - 50, off_x - 70, off_y - 90)
        # Borde delantero del clic izquierdo
        cr.curve_to(off_x - 70, off_y - 128, off_x - 66, off_y - 162, off_x - 42, off_y - 188)
        cr.close_path()

    def _draw_mouse_body(self, cr: cairo.Context):
        # 1. Sombra suave ambiental proyectada en múltiples pasos
        for off_y, alpha in [(16, 0.12), (10, 0.22), (5, 0.38), (2, 0.55)]:
            cr.save()
            cr.translate(2, off_y)
            self._mouse_outline_path(cr)
            cr.set_source_rgba(0.0, 0.0, 0.0, alpha)
            cr.fill()
            cr.restore()

        # 2. Carcasa base exterior (Chasis en compuesto oscuro texturizado)
        self._mouse_outline_path(cr)
        base_pat = cairo.LinearGradient(-80, -180, 80, 200)
        base_pat.add_color_stop_rgb(0.0, 0.12, 0.13, 0.16)
        base_pat.add_color_stop_rgb(0.5, 0.07, 0.08, 0.09)
        base_pat.add_color_stop_rgb(1.0, 0.04, 0.05, 0.06)
        cr.set_source(base_pat)
        cr.fill_preserve()
        cr.set_line_width(1.4)
        cr.set_source_rgba(0.24, 0.28, 0.35, 0.7)
        cr.stroke()

        # 3. Aleta del pulgar (Thumb Rest Wing) con acabado biselado
        cr.save()
        cr.new_path()
        cr.move_to(-52, -25)
        cr.curve_to(-86, -14, -108, 22, -102, 54)
        cr.curve_to(-98, 76, -74, 98, -52, 98)
        cr.line_to(-50, 35)
        cr.close_path()

        wing_pat = cairo.LinearGradient(-108, 20, -50, 60)
        wing_pat.add_color_stop_rgb(0.0, 0.14, 0.16, 0.19)
        wing_pat.add_color_stop_rgb(0.6, 0.09, 0.10, 0.12)
        wing_pat.add_color_stop_rgb(1.0, 0.15, 0.17, 0.20)
        cr.set_source(wing_pat)
        cr.fill_preserve()
        cr.set_line_width(1.3)
        cr.set_source_rgba(0.38, 0.45, 0.54, 0.8)
        cr.stroke()

        # Almohadilla antideslizante con textura geométrica isométrica
        cr.save()
        cr.new_path()
        cr.move_to(-56, 15)
        cr.curve_to(-92, 24, -96, 56, -90, 74)
        cr.curve_to(-82, 85, -68, 92, -54, 90)
        cr.close_path()
        cr.clip()

        cr.set_source_rgba(0.03, 0.03, 0.04, 0.90)
        cr.paint()

        cr.set_line_width(0.8)
        cr.set_source_rgba(0.0, 0.898, 1.0, 0.10)
        for gx in range(-115, -35, 7):
            cr.move_to(gx, -10)
            cr.line_to(gx + 35, 110)
            cr.stroke()
            cr.move_to(gx + 35, -10)
            cr.line_to(gx, 110)
            cr.stroke()
        cr.restore()
        cr.restore()

        # 4. Flanco derecho con textura de goma ergonómica
        cr.save()
        cr.new_path()
        cr.move_to(58, -65)
        cr.curve_to(74, -20, 78, 30, 72, 80)
        cr.curve_to(68, 115, 54, 142, 46, 158)
        cr.line_to(40, 150)
        cr.curve_to(48, 120, 56, 70, 54, 20)
        cr.curve_to(52, -20, 46, -55, 58, -65)
        cr.close_path()

        rgrip_pat = cairo.LinearGradient(40, 0, 78, 0)
        rgrip_pat.add_color_stop_rgb(0.0, 0.10, 0.11, 0.13)
        rgrip_pat.add_color_stop_rgb(1.0, 0.05, 0.05, 0.06)
        cr.set_source(rgrip_pat)
        cr.fill_preserve()
        cr.set_line_width(0.8)
        cr.set_source_rgba(0.24, 0.28, 0.35, 0.5)
        cr.stroke()

        # Ranuras horizontales contorneadas para sujeción
        cr.set_line_width(1.5)
        cr.set_source_rgba(0.02, 0.02, 0.03, 0.9)
        for gy in range(-45, 135, 15):
            cr.move_to(48, gy)
            cr.curve_to(58, gy + 4, 68, gy + 9, 72, gy + 7)
            cr.stroke()
        cr.restore()

    def _draw_mouse_details(self, cr: cairo.Context):
        r_led, g_led, b_led = self._led_color_rgb

        # 1. Carcasa del lomo (Palm Rest) con volumen 3D y brillo especular
        cr.save()
        cr.new_path()
        cr.move_to(0, -32)
        cr.line_to(-46, -20)
        cr.curve_to(-58, 20, -60, 80, -56, 125)
        cr.curve_to(-50, 162, -28, 185, 0, 185)
        cr.curve_to(28, 185, 50, 162, 56, 125)
        cr.curve_to(60, 80, 58, 20, 46, -20)
        cr.close_path()

        palm_pat = cairo.LinearGradient(-40, -20, 40, 180)
        palm_pat.add_color_stop_rgb(0.0, 0.20, 0.22, 0.26)
        palm_pat.add_color_stop_rgb(0.35, 0.15, 0.16, 0.19)
        palm_pat.add_color_stop_rgb(0.8, 0.10, 0.11, 0.13)
        palm_pat.add_color_stop_rgb(1.0, 0.06, 0.07, 0.08)
        cr.set_source(palm_pat)
        cr.fill_preserve()
        cr.set_line_width(1.6)
        cr.set_source_rgba(0.30, 0.36, 0.45, 0.75)
        cr.stroke()

        # Brillo especular longitudinal sobre la cresta central
        cr.save()
        cr.set_line_width(1.2)
        spine_pat = cairo.LinearGradient(-12, -24, -12, 175)
        spine_pat.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.28)
        spine_pat.add_color_stop_rgba(0.4, 1.0, 1.0, 1.0, 0.10)
        spine_pat.add_color_stop_rgba(1.0, 1.0, 1.0, 1.0, 0.0)
        cr.set_source(spine_pat)
        cr.move_to(-12, -24)
        cr.curve_to(-18, 40, -16, 110, -4, 175)
        cr.stroke()
        cr.restore()

        # 2. Logotipo G retroiluminado con halo difuso reactivo
        cr.save()
        cr.translate(0, 82)
        bloom = cairo.RadialGradient(0, 0, 2, 0, 0, 38)
        bloom.add_color_stop_rgba(0.0, r_led, g_led, b_led, 0.70)
        bloom.add_color_stop_rgba(0.35, r_led, g_led, b_led, 0.30)
        bloom.add_color_stop_rgba(0.75, r_led, g_led, b_led, 0.08)
        bloom.add_color_stop_rgba(1.0, r_led, g_led, b_led, 0.0)
        cr.set_source(bloom)
        cr.arc(0, 0, 38, 0, 2 * math.pi)
        cr.fill()

        # Lente oscura interna
        cr.set_source_rgba(0.05, 0.06, 0.08, 0.90)
        cr.arc(0, 0, 20, 0, 2 * math.pi)
        cr.fill_preserve()
        cr.set_line_width(1.0)
        cr.set_source_rgba(r_led, g_led, b_led, 0.4)
        cr.stroke()

        # Letra 'G' estilizada de precisión
        cr.set_source_rgba(r_led, g_led, b_led, 0.95)
        cr.set_line_width(4.0)
        cr.arc(0, 0, 13.5, 0.22 * math.pi, 1.82 * math.pi)
        cr.stroke()
        cr.move_to(-1, 0)
        cr.line_to(13.5, 0)
        cr.stroke()

        # Reflejo interior brillante
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.75)
        cr.set_line_width(1.3)
        cr.arc(0, 0, 13.5, 0.35 * math.pi, 1.65 * math.pi)
        cr.stroke()
        cr.restore()
        cr.restore()

        # 3. Palas de clic primario (Clic izquierdo M1 y Clic derecho M2)
        # M1 (Izquierdo)
        cr.save()
        cr.new_path()
        cr.move_to(-12, -35)
        cr.line_to(-12, -188)
        cr.line_to(-42, -188)
        cr.line_to(-66, -160)
        cr.line_to(-64, -118)
        cr.curve_to(-60, -80, -54, -45, -46, -24)
        cr.close_path()

        m1_pat = cairo.LinearGradient(-66, -180, -12, -30)
        m1_pat.add_color_stop_rgb(0.0, 0.21, 0.23, 0.28)
        m1_pat.add_color_stop_rgb(0.4, 0.15, 0.16, 0.19)
        m1_pat.add_color_stop_rgb(1.0, 0.09, 0.10, 0.12)
        cr.set_source(m1_pat)
        cr.fill_preserve()
        cr.set_line_width(1.5)
        cr.set_source_rgba(0.32, 0.38, 0.48, 0.8)
        cr.stroke()
        cr.restore()

        # M2 (Derecho)
        cr.save()
        cr.new_path()
        cr.move_to(12, -35)
        cr.line_to(12, -182)
        cr.line_to(48, -182)
        cr.line_to(68, -152)
        cr.curve_to(70, -100, 62, -55, 46, -24)
        cr.close_path()

        m2_pat = cairo.LinearGradient(12, -180, 70, -30)
        m2_pat.add_color_stop_rgb(0.0, 0.19, 0.21, 0.24)
        m2_pat.add_color_stop_rgb(0.4, 0.13, 0.14, 0.16)
        m2_pat.add_color_stop_rgb(1.0, 0.08, 0.09, 0.10)
        cr.set_source(m2_pat)
        cr.fill_preserve()
        cr.set_line_width(1.5)
        cr.set_source_rgba(0.30, 0.35, 0.44, 0.75)
        cr.stroke()
        cr.restore()

        # 4. Zócalo central y Rueda de desplazamiento metálica con estrías
        cr.save()
        cr.rectangle(-14, -165, 28, 140)
        well_pat = cairo.LinearGradient(0, -165, 0, -25)
        well_pat.add_color_stop_rgb(0.0, 0.03, 0.03, 0.04)
        well_pat.add_color_stop_rgb(0.5, 0.02, 0.02, 0.03)
        well_pat.add_color_stop_rgb(1.0, 0.05, 0.06, 0.07)
        cr.set_source(well_pat)
        cr.fill_preserve()
        cr.set_line_width(1.2)
        cr.set_source_rgba(0.20, 0.24, 0.30, 0.6)
        cr.stroke()

        wheel_y = -152
        wheel_h = 56

        # Bandas de aluminio laterales de la rueda
        rim_l = cairo.LinearGradient(-9, wheel_y, -6, wheel_y + wheel_h)
        rim_l.add_color_stop_rgb(0.0, 0.50, 0.55, 0.64)
        rim_l.add_color_stop_rgb(0.5, 0.82, 0.88, 0.96)
        rim_l.add_color_stop_rgb(1.0, 0.40, 0.45, 0.52)
        cr.set_source(rim_l)
        cr.rectangle(-9, wheel_y, 4, wheel_h)
        cr.fill()

        rim_r = cairo.LinearGradient(6, wheel_y, 9, wheel_y + wheel_h)
        rim_r.add_color_stop_rgb(0.0, 0.50, 0.55, 0.64)
        rim_r.add_color_stop_rgb(0.5, 0.82, 0.88, 0.96)
        rim_r.add_color_stop_rgb(1.0, 0.40, 0.45, 0.52)
        cr.set_source(rim_r)
        cr.rectangle(5, wheel_y, 4, wheel_h)
        cr.fill()

        # Banda de goma central
        cr.rectangle(-5, wheel_y, 10, wheel_h)
        tire_pat = cairo.LinearGradient(-5, 0, 5, 0)
        tire_pat.add_color_stop_rgb(0.0, 0.09, 0.10, 0.12)
        tire_pat.add_color_stop_rgb(0.5, 0.20, 0.22, 0.26)
        tire_pat.add_color_stop_rgb(1.0, 0.09, 0.10, 0.12)
        cr.set_source(tire_pat)
        cr.fill_preserve()
        cr.set_line_width(1.0)
        cr.set_source_rgba(0.5, 0.6, 0.7, 0.4)
        cr.stroke()

        # Estrías de relieve 3D en la rueda
        for ry in range(int(wheel_y + 4), int(wheel_y + wheel_h - 2), 6):
            cr.set_line_width(1.2)
            cr.set_source_rgba(0.02, 0.02, 0.03, 0.9)
            cr.move_to(-5, ry + 1)
            cr.line_to(5, ry + 1)
            cr.stroke()
            cr.set_line_width(1.0)
            cr.set_source_rgba(0.45, 0.55, 0.65, 0.8)
            cr.move_to(-5, ry)
            cr.line_to(5, ry)
            cr.stroke()

        # Flechas de inclinación tilt de rueda
        cr.set_line_width(1.0)
        is_wl_hov = (self._hovered_button == "WHEEL_LEFT")
        is_wr_hov = (self._hovered_button == "WHEEL_RIGHT")
        cr.set_source_rgba(0.0, 0.898, 1.0, 0.95 if is_wl_hov else 0.65)
        cr.move_to(-11, -126)
        cr.line_to(-13, -124)
        cr.line_to(-11, -122)
        cr.stroke()
        cr.set_source_rgba(0.0, 0.898, 1.0, 0.95 if is_wr_hov else 0.65)
        cr.move_to(11, -126)
        cr.line_to(13, -124)
        cr.line_to(11, -122)
        cr.stroke()

        # Pulsador mecánico de liberación de rueda (Clutch)
        self._draw_round_rect(cr, -6, -90, 12, 16, 2)
        clutch_pat = cairo.LinearGradient(-6, -90, 6, -74)
        clutch_pat.add_color_stop_rgb(0.0, 0.30, 0.34, 0.40)
        clutch_pat.add_color_stop_rgb(1.0, 0.13, 0.15, 0.18)
        cr.set_source(clutch_pat)
        cr.fill_preserve()
        cr.set_line_width(1.0)
        cr.set_source_rgba(0.42, 0.48, 0.58, 0.6)
        cr.stroke()

        # Botón G9 de cambio de perfil
        is_g9_hov = (self._hovered_button == "G9")
        self._draw_round_rect(cr, -8, -66, 16, 24, 3)
        g9_pat = cairo.LinearGradient(-8, -66, 8, -42)
        g9_pat.add_color_stop_rgb(0.0, 0.24, 0.27, 0.33)
        g9_pat.add_color_stop_rgb(0.6, 0.15, 0.17, 0.20)
        g9_pat.add_color_stop_rgb(1.0, 0.09, 0.10, 0.12)
        cr.set_source(g9_pat)
        cr.fill_preserve()
        cr.set_line_width(1.2)
        cr.set_source_rgba(0.0, 0.898, 1.0, 0.85 if is_g9_hov else 0.45)
        cr.stroke()
        cr.set_source_rgba(0.0, 0.898, 1.0, 0.95 if is_g9_hov else 0.55)
        cr.arc(0, -54, 2.5, 0, 2 * math.pi)
        cr.fill()
        cr.restore()

        # 5. Botones laterales G8 y G7 (+20-25% tamaño, bajados y girados a la izq en línea con los LEDs)
        # G8 (DPI Up)
        is_g8_hov = (self._hovered_button == "G8")
        cr.save()
        cr.new_path()
        cr.move_to(-65, -136)
        cr.line_to(-51, -133)
        cr.line_to(-46, -110)
        cr.line_to(-60, -113)
        cr.close_path()
        g8_pat = cairo.LinearGradient(-65, -136, -46, -110)
        g8_pat.add_color_stop_rgb(0.0, 0.28, 0.32, 0.38)
        g8_pat.add_color_stop_rgb(1.0, 0.13, 0.15, 0.18)
        cr.set_source(g8_pat)
        cr.fill_preserve()
        cr.set_line_width(1.2)
        cr.set_source_rgba(0.0, 0.898, 1.0, 0.85 if is_g8_hov else 0.45)
        cr.stroke()
        # Flecha Up ▲ alineada en el eje
        cr.set_source_rgba(0.0, 0.898, 1.0, 0.95 if is_g8_hov else 0.70)
        cr.move_to(-56, -127)
        cr.line_to(-52, -121)
        cr.line_to(-59, -122)
        cr.close_path()
        cr.fill()
        cr.restore()

        # G7 (DPI Down)
        is_g7_hov = (self._hovered_button == "G7")
        cr.save()
        cr.new_path()
        cr.move_to(-59, -107)
        cr.line_to(-46, -104)
        cr.line_to(-41, -81)
        cr.line_to(-54, -84)
        cr.close_path()
        g7_pat = cairo.LinearGradient(-59, -107, -41, -81)
        g7_pat.add_color_stop_rgb(0.0, 0.25, 0.28, 0.34)
        g7_pat.add_color_stop_rgb(1.0, 0.11, 0.12, 0.15)
        cr.set_source(g7_pat)
        cr.fill_preserve()
        cr.set_line_width(1.2)
        cr.set_source_rgba(0.0, 0.898, 1.0, 0.85 if is_g7_hov else 0.45)
        cr.stroke()
        # Flecha Down ▼ alineada en el eje
        cr.set_source_rgba(0.0, 0.898, 1.0, 0.95 if is_g7_hov else 0.70)
        cr.move_to(-51, -97)
        cr.line_to(-44, -96)
        cr.line_to(-47, -90)
        cr.close_path()
        cr.fill()
        cr.restore()

        # 6. Indicadores LED de DPI bajados hasta el fondo/borde inferior de M1
        dpi_led_positions = [
            (-48, -68),
            (-44, -52),
            (-40, -36),
        ]
        for bar_x, bar_y in dpi_led_positions:
            cr.save()
            glow = cairo.RadialGradient(bar_x, bar_y, 1, bar_x, bar_y, 9)
            glow.add_color_stop_rgba(0.0, r_led, g_led, b_led, 0.80)
            glow.add_color_stop_rgba(1.0, r_led, g_led, b_led, 0.0)
            cr.set_source(glow)
            cr.arc(bar_x, bar_y, 9, 0, 2 * math.pi)
            cr.fill()

            cr.new_path()
            cr.move_to(bar_x - 3.5, bar_y - 3.5)
            cr.line_to(bar_x + 3.0, bar_y - 2.0)
            cr.line_to(bar_x + 1.5, bar_y + 4.0)
            cr.line_to(bar_x - 5.0, bar_y + 2.5)
            cr.close_path()
            cr.set_source_rgba(r_led, g_led, b_led, 0.95)
            cr.fill_preserve()
            cr.set_line_width(0.6)
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.90)
            cr.stroke()
            cr.restore()

        # 7. Botones laterales: SNIPER (en aleta pulgar) y G5/G4 emparejados abajo
        # Botón SNIPER (Aleta izquierda, adelantado y arriba de G5)
        is_snip_hov = (self._hovered_button == "SNIPER")
        cr.save()
        snip_x = -88
        snip_y = -32
        snip_w = 17
        snip_h = 22
        self._draw_round_rect(cr, snip_x, snip_y, snip_w, snip_h, 5)
        snip_pat = cairo.LinearGradient(snip_x, snip_y, snip_x + snip_w, snip_y + snip_h)
        snip_pat.add_color_stop_rgb(0.0, 0.30, 0.35, 0.42)
        snip_pat.add_color_stop_rgb(0.6, 0.16, 0.19, 0.23)
        snip_pat.add_color_stop_rgb(1.0, 0.10, 0.12, 0.15)
        cr.set_source(snip_pat)
        cr.fill_preserve()
        cr.set_line_width(1.4)
        cr.set_source_rgba(0.0, 0.898, 1.0, 0.90 if is_snip_hov else 0.50)
        cr.stroke()

        # Diana reticular de precisión
        center_sx = snip_x + snip_w / 2
        center_sy = snip_y + snip_h / 2
        cr.translate(center_sx, center_sy)
        cr.set_line_width(1.1)
        cr.set_source_rgba(0.0, 0.898, 1.0, 0.95 if is_snip_hov else 0.75)
        cr.arc(0, 0, 4.5, 0, 2 * math.pi)
        cr.stroke()
        cr.move_to(-6.0, 0)
        cr.line_to(6.0, 0)
        cr.stroke()
        cr.move_to(0, -6.0)
        cr.line_to(0, 6.0)
        cr.stroke()
        cr.restore()

        # G5 (Delantero: +25% largo subiendo hacia arriba, de y=-7 a y=16)
        is_g5_hov = (self._hovered_button == "G5")
        cr.save()
        cr.new_path()
        cr.move_to(-65, -7)
        cr.line_to(-49, -5)
        cr.line_to(-51, 16)
        cr.line_to(-67, 14)
        cr.close_path()
        g5_pat = cairo.LinearGradient(-67, -7, -49, 16)
        g5_pat.add_color_stop_rgb(0.0, 0.28, 0.32, 0.38)
        g5_pat.add_color_stop_rgb(0.5, 0.17, 0.19, 0.23)
        g5_pat.add_color_stop_rgb(1.0, 0.11, 0.12, 0.14)
        cr.set_source(g5_pat)
        cr.fill_preserve()
        cr.set_line_width(1.3)
        cr.set_source_rgba(0.0, 0.898, 1.0, 0.85 if is_g5_hov else 0.45)
        cr.stroke()
        cr.restore()

        # G4 (Trasero: +25% largo subiendo acoplado a G5, de y=19 a y=42)
        is_g4_hov = (self._hovered_button == "G4")
        cr.save()
        cr.new_path()
        cr.move_to(-67, 19)
        cr.line_to(-51, 21)
        cr.line_to(-53, 42)
        cr.line_to(-69, 40)
        cr.close_path()
        g4_pat = cairo.LinearGradient(-69, 19, -51, 42)
        g4_pat.add_color_stop_rgb(0.0, 0.26, 0.30, 0.36)
        g4_pat.add_color_stop_rgb(0.5, 0.15, 0.17, 0.20)
        g4_pat.add_color_stop_rgb(1.0, 0.09, 0.10, 0.12)
        cr.set_source(g4_pat)
        cr.fill_preserve()
        cr.set_line_width(1.3)
        cr.set_source_rgba(0.0, 0.898, 1.0, 0.85 if is_g4_hov else 0.45)
        cr.stroke()
        cr.restore()

    def _draw_buttons_and_callouts(self, cr: cairo.Context, cx: float, cy: float, scale: float):
        """
        Dibuja los pines interactivos con líneas guía técnicas biseladas a 45 grados y tarjetas HUD.
        """
        assignments = {}
        if self._current_profile:
            for asgn in self._current_profile.list_assignments():
                assignments[asgn.button.button_id] = asgn.action

        # Coordenadas físicas en el ratón y posiciones exteriores de las tarjetas HUD
        left_x = -196
        right_x = 98
        tag_w = 98
        tag_h = 24

        cards_data: list[tuple[str, float, float, float, float]] = [
            # Laterales izquierdos ordenados estrictamente de arriba hacia abajo (btn_id, pin_x, pin_y, tag_x, tag_y)
            ("LEFT", -28, -165, left_x, -180),
            ("G8", -55.5, -123, left_x, -135),
            ("G7", -50.0, -94, left_x, -95),
            ("SNIPER", -79.5, -21, left_x, -55),
            ("G5", -57, 5, left_x, -10),
            ("G4", -59, 31, left_x, 35),

            # Superiores y flanco derecho ordenados de arriba hacia abajo
            ("RIGHT", 28, -165, right_x, -180),
            ("MIDDLE", 0, -135, right_x, -135),
            ("WHEEL_RIGHT", 13, -118, right_x, -95),
            ("G9", 0, -54, right_x, -55),
        ]

        r_accent, g_accent, b_accent = (0.0, 0.898, 1.0)  # Cian futurista de acento

        for btn_id, pin_x, pin_y, tag_x, tag_y in cards_data:
            action = assignments.get(btn_id)
            is_hovered = (self._hovered_button == btn_id)
            is_left = (tag_x < 0)

            # 1. Punto de anclaje luminoso en el ratón (Pin con halo)
            cr.save()
            cr.new_path()
            if is_hovered:
                glow = cairo.RadialGradient(pin_x, pin_y, 1, pin_x, pin_y, 11)
                glow.add_color_stop_rgba(0.0, r_accent, g_accent, b_accent, 0.85)
                glow.add_color_stop_rgba(1.0, r_accent, g_accent, b_accent, 0.0)
                cr.set_source(glow)
                cr.arc(pin_x, pin_y, 11, 0, 2 * math.pi)
                cr.fill()

                cr.new_path()
                cr.set_source_rgba(1.0, 1.0, 1.0, 1.0)
                cr.arc(pin_x, pin_y, 4.0, 0, 2 * math.pi)
                cr.fill_preserve()
                cr.set_line_width(1.8)
                cr.set_source_rgba(r_accent, g_accent, b_accent, 1.0)
                cr.stroke()
            else:
                cr.set_source_rgba(0.12, 0.16, 0.22, 0.85)
                cr.arc(pin_x, pin_y, 3.5, 0, 2 * math.pi)
                cr.fill_preserve()
                cr.set_line_width(1.2)
                cr.set_source_rgba(r_accent, g_accent, b_accent, 0.8)
                cr.stroke()
            cr.restore()

            # 2. Línea guía técnica biselada a 45 grados (Tarjeta -> Ratón)
            cr.save()
            cr.new_path()
            cr.set_line_width(1.4 if is_hovered else 0.85)
            cr.set_source_rgba(r_accent, g_accent, b_accent, 0.95 if is_hovered else 0.40)

            card_conn_x = (tag_x + tag_w) if is_left else tag_x
            card_conn_y = tag_y + (tag_h / 2.0)

            cr.move_to(card_conn_x, card_conn_y)
            dy = pin_y - card_conn_y
            if is_left:
                elbow_x = pin_x - abs(dy) - 6
                elbow_x = max(card_conn_x + 12, min(elbow_x, pin_x - 6))
                cr.line_to(elbow_x, card_conn_y)
                cr.line_to(elbow_x + abs(dy), pin_y)
                cr.line_to(pin_x, pin_y)
            else:
                elbow_x = pin_x + abs(dy) + 6
                elbow_x = min(card_conn_x - 12, max(elbow_x, pin_x + 6))
                cr.line_to(elbow_x, card_conn_y)
                cr.line_to(elbow_x - abs(dy), pin_y)
                cr.line_to(pin_x, pin_y)
            cr.stroke()
            cr.restore()

            # 3. Registro de caja delimitadora para colisiones de clic y hover
            screen_x1 = cx + (tag_x * scale)
            screen_y1 = cy + (tag_y * scale)
            screen_x2 = screen_x1 + (tag_w * scale)
            screen_y2 = screen_y1 + (tag_h * scale)
            self._hit_targets[btn_id] = (screen_x1, screen_y1, screen_x2, screen_y2)

            # 4. Tarjeta HUD flotante de estilo glassmorphism
            cr.save()
            cr.new_path()
            self._draw_round_rect(cr, tag_x, tag_y, tag_w, tag_h, 4)

            if is_hovered:
                card_pat = cairo.LinearGradient(tag_x, tag_y, tag_x + tag_w, tag_y + tag_h)
                card_pat.add_color_stop_rgba(0.0, 0.0, 0.898, 1.0, 0.28)
                card_pat.add_color_stop_rgba(1.0, 0.09, 0.13, 0.20, 0.95)
                cr.set_source(card_pat)
                cr.fill_preserve()
                cr.set_line_width(1.4)
                cr.set_source_rgba(r_accent, g_accent, b_accent, 0.95)
                cr.stroke()
            elif action:
                card_pat = cairo.LinearGradient(tag_x, tag_y, tag_x + tag_w, tag_y + tag_h)
                card_pat.add_color_stop_rgba(0.0, 0.11, 0.16, 0.24, 0.95)
                card_pat.add_color_stop_rgba(1.0, 0.08, 0.10, 0.14, 0.90)
                cr.set_source(card_pat)
                cr.fill_preserve()
                cr.set_line_width(0.9)
                cr.set_source_rgba(0.0, 0.898, 1.0, 0.50)
                cr.stroke()
            else:
                cr.set_source_rgba(0.09, 0.11, 0.14, 0.92)
                cr.fill_preserve()
                cr.set_line_width(0.8)
                cr.set_source_rgba(0.26, 0.34, 0.44, 0.55)
                cr.stroke()

            # Píldora indicadora vertical de estado a la izquierda
            cr.new_path()
            pill_x = tag_x + 3
            self._draw_round_rect(cr, pill_x, tag_y + 4, 3, tag_h - 8, 1.5)
            if is_hovered or action:
                cr.set_source_rgba(r_accent, g_accent, b_accent, 0.95 if is_hovered else 0.70)
            else:
                cr.set_source_rgba(0.4, 0.45, 0.55, 0.40)
            cr.fill()

            # Tipografía del botón
            cr.set_font_size(8.5)
            cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            if is_hovered:
                cr.set_source_rgb(0.0, 0.898, 1.0)
            else:
                cr.set_source_rgb(0.96, 0.98, 1.0)
            cr.move_to(tag_x + 10, tag_y + 10.5)
            cr.show_text(btn_id)

            # Subtexto de acción asignada o tecla
            cr.set_font_size(7.0)
            cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
            if action:
                cr.set_source_rgba(0.0, 0.898, 1.0, 0.95 if is_hovered else 0.75)
                name_disp = _(action.name)
                if len(name_disp) > 10:
                    name_disp = name_disp[:9] + "…"
                txt = f"[{action.binding_value}] {name_disp}"
            else:
                cr.set_source_rgba(0.60, 0.65, 0.72, 0.50)
                txt = _("Sin asignar")

            cr.move_to(tag_x + 10, tag_y + 19.5)
            cr.show_text(txt)
            cr.restore()

    # ---------------------------------------------------------
    # Manejo de Interacción y Eventos
    # ---------------------------------------------------------
    def _find_hit_button(self, x: float, y: float) -> str | None:
        """Determina si un punto (x, y) de la pantalla colisiona con un botón."""
        for btn_id, (bx1, by1, bx2, by2) in self._hit_targets.items():
            if bx1 <= x <= bx2 and by1 <= y <= by2:
                return btn_id
        return None

    def _on_motion(self, _controller, x: float, y: float):
        btn_id = self._find_hit_button(x, y)
        if btn_id != self._hovered_button:
            self._hovered_button = btn_id
            self.queue_draw()

            # Cambiar cursor a mano si se posa sobre un botón interactivo
            if btn_id:
                self.set_cursor_from_name("pointer")
            else:
                self.set_cursor(None)

    def _on_leave(self, _controller):
        if self._hovered_button is not None:
            self._hovered_button = None
            self.set_cursor(None)
            self.queue_draw()

    def _on_click_pressed(self, _gesture, _n_press: int, x: float, y: float):
        btn_id = self._find_hit_button(x, y)
        if btn_id and self._on_button_clicked:
            meta = BUTTON_METADATA.get(btn_id, {"name": f"Botón {btn_id}"})
            btn_name = str(meta["name"])
            self._on_button_clicked(btn_id, btn_name)
