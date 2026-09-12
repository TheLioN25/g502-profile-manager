"""
Componente visual e interactivo del ratón Logitech G502 HERO (GTK4 + Cairo).
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
    Área de dibujo vectorial interactiva que representa el ratón Logitech G502 HERO.
    Muestra los 11 botones físicos, sus líneas guía y acciones asignadas.
    Permite hacer clic sobre cualquier botón para abrir el diálogo de configuración.
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

        # Fondo sutil del contenedor
        cr.set_source_rgba(0.08, 0.09, 0.11, 1.0)
        cr.paint()

        # Cuadrícula sutil de fondo estilo técnico/blueprint
        cr.set_line_width(0.5)
        cr.set_source_rgba(1.0, 1.0, 1.0, 0.03)
        for x in range(0, width, 24):
            cr.move_to(x, 0)
            cr.line_to(x, height)
            cr.stroke()
        for y in range(0, height, 24):
            cr.move_to(0, y)
            cr.line_to(width, y)
            cr.stroke()

        # Centro del ratón en la vista
        cx = width * 0.50
        cy = height * 0.50
        natural_w = 390.0
        natural_h = 420.0
        scale = min(width / natural_w, height / natural_h) * 0.90
        scale = max(0.65, min(scale, 2.5))

        cr.save()
        cr.translate(cx, cy)
        cr.scale(scale, scale)

        # 1. Silueta principal del Logitech G502 HERO
        self._draw_mouse_body(cr)

        # 2. Acabados y detalles internos (Rueda, logotipo G, luces DPI)
        self._draw_mouse_details(cr)

        # 3. Puntos de anclaje de botones en el ratón y etiquetas con líneas guía
        self._draw_buttons_and_callouts(cr, cx, cy, scale)

        cr.restore()

    def _draw_mouse_body(self, cr: cairo.Context):
        # Sombra exterior del ratón
        cr.save()
        cr.set_source_rgba(0.0, 0.0, 0.0, 0.45)
        self._mouse_outline_path(cr, offset_x=4, offset_y=8)
        cr.fill()
        cr.restore()

        # Carcasa base exterior (Chasis oscuro texturizado)
        self._mouse_outline_path(cr)
        chassis_pat = cairo.LinearGradient(-80, -180, 80, 200)
        chassis_pat.add_color_stop_rgb(0.0, 0.16, 0.17, 0.20)
        chassis_pat.add_color_stop_rgb(0.5, 0.11, 0.12, 0.14)
        chassis_pat.add_color_stop_rgb(1.0, 0.07, 0.08, 0.09)
        cr.set_source(chassis_pat)
        cr.fill_preserve()

        # Borde metálico exterior
        cr.set_line_width(1.8)
        cr.set_source_rgba(0.28, 0.32, 0.38, 0.7)
        cr.stroke()

        # Aleta del pulgar (Thumb Wing) - Borde izquierdo inferior
        cr.save()
        cr.move_to(-52, -20)
        cr.curve_to(-95, -10, -105, 60, -60, 95)
        cr.line_to(-50, 60)
        cr.close_path()
        wing_pat = cairo.LinearGradient(-105, 0, -50, 60)
        wing_pat.add_color_stop_rgb(0.0, 0.10, 0.11, 0.13)
        wing_pat.add_color_stop_rgb(1.0, 0.15, 0.16, 0.18)
        cr.set_source(wing_pat)
        cr.fill_preserve()
        cr.set_line_width(1.2)
        cr.set_source_rgba(0.3, 0.35, 0.4, 0.5)
        cr.stroke()
        cr.restore()

        # Grips de textura de goma en el lateral derecho
        cr.set_line_width(1.0)
        cr.set_source_rgba(0.05, 0.05, 0.06, 0.8)
        for i in range(4):
            cr.move_to(55 + i * 2, -10 + i * 18)
            cr.curve_to(62 + i * 2, 20 + i * 18, 58 + i * 2, 50 + i * 18, 48 + i * 2, 80 + i * 15)
            cr.stroke()

    def _mouse_outline_path(self, cr: cairo.Context, offset_x: float = 0, offset_y: float = 0):
        cr.new_sub_path()
        cr.move_to(offset_x + 0, offset_y - 180)
        # Clic derecho borde
        cr.curve_to(offset_x + 45, offset_y - 175, offset_x + 65, offset_y - 120, offset_x + 68, offset_y - 50)
        # Lateral derecho centro
        cr.curve_to(offset_x + 72, offset_y + 10, offset_x + 68, offset_y + 70, offset_x + 60, offset_y + 120)
        # Parte trasera derecha a centro
        cr.curve_to(offset_x + 55, offset_y + 160, offset_x + 30, offset_y + 185, offset_x + 0, offset_y + 185)
        # Parte trasera centro a izquierda
        cr.curve_to(offset_x - 30, offset_y + 185, offset_x - 55, offset_y + 155, offset_x - 60, offset_y + 110)
        # Aleta del pulgar
        cr.curve_to(offset_x - 70, offset_y + 80, offset_x - 100, offset_y + 45, offset_x - 90, offset_y - 10)
        # Lateral izquierdo delantero
        cr.curve_to(offset_x - 85, offset_y - 35, offset_x - 68, offset_y - 70, offset_x - 65, offset_y - 110)
        # Clic izquierdo
        cr.curve_to(offset_x - 60, offset_y - 150, offset_x - 35, offset_y - 178, offset_x + 0, offset_y - 180)
        cr.close_path()

    def _draw_mouse_details(self, cr: cairo.Context):
        # Surco de separación entre clic izquierdo y derecho
        cr.set_line_width(1.5)
        cr.set_source_rgba(0.05, 0.05, 0.06, 0.9)
        cr.move_to(0, -180)
        cr.line_to(0, -145)
        cr.stroke()

        cr.move_to(0, -85)
        cr.line_to(0, -45)
        cr.stroke()

        # Hueco de la rueda de desplazamiento
        cr.set_source_rgba(0.04, 0.04, 0.05, 1.0)
        cr.rectangle(-12, -145, 24, 60)
        cr.fill()

        # Rueda de desplazamiento metálica con gomas
        wheel_pat = cairo.LinearGradient(-10, -140, 10, -90)
        wheel_pat.add_color_stop_rgb(0.0, 0.45, 0.48, 0.55)
        wheel_pat.add_color_stop_rgb(0.5, 0.22, 0.24, 0.28)
        wheel_pat.add_color_stop_rgb(1.0, 0.50, 0.52, 0.58)
        cr.set_source(wheel_pat)
        cr.rectangle(-9, -140, 18, 50)
        cr.fill_preserve()
        cr.set_line_width(1.0)
        cr.set_source_rgba(0.7, 0.75, 0.85, 0.6)
        cr.stroke()

        # Estrías de la rueda
        cr.set_line_width(1.2)
        cr.set_source_rgba(0.08, 0.08, 0.09, 0.9)
        for y in range(-135, -92, 6):
            cr.move_to(-8, y)
            cr.line_to(8, y)
            cr.stroke()

        # Franjas LED de DPI en el flanco izquierdo (3 barritas diagonales)
        r, g, b = self._led_color_rgb
        for i in range(3):
            cr.save()
            cr.set_source_rgba(r, g, b, 0.9)
            cr.move_to(-56 + i * 2, -100 + i * 14)
            cr.line_to(-52 + i * 2, -96 + i * 14)
            cr.line_to(-56 + i * 2, -90 + i * 14)
            cr.line_to(-60 + i * 2, -94 + i * 14)
            cr.close_path()
            cr.fill()
            cr.restore()

        # Logotipo "G" de Logitech iluminado con brillo LED
        cr.save()
        cr.translate(-2, 70)
        # Resplandor suave del logo
        glow = cairo.RadialGradient(0, 0, 4, 0, 0, 26)
        glow.add_color_stop_rgba(0.0, r, g, b, 0.5)
        glow.add_color_stop_rgba(1.0, r, g, b, 0.0)
        cr.set_source(glow)
        cr.arc(0, 0, 26, 0, 2 * math.pi)
        cr.fill()

        # Letra 'G' estilizada
        cr.set_source_rgba(r, g, b, 0.95)
        cr.set_line_width(3.6)
        cr.arc(0, 0, 14, 0.25 * math.pi, 1.85 * math.pi)
        cr.stroke()
        cr.move_to(0, 0)
        cr.line_to(14, 0)
        cr.stroke()
        cr.restore()

    def _draw_buttons_and_callouts(self, cr: cairo.Context, cx: float, cy: float, scale: float):
        """
        Dibuja los botones interactivos con sus líneas conectoras y tarjetas de texto.
        """
        assignments = {}
        if self._current_profile:
            for asgn in self._current_profile.list_assignments():
                assignments[asgn.button.button_id] = asgn.action

        # Coordenadas físicas en el ratón (x, y) y posición de la etiqueta exterior (tag_x, tag_y)
        button_coords: dict[str, tuple[float, float, float, float]] = {
            # Laterales izquierdos (pin_x, pin_y, tag_x, tag_y)
            "G8": (-48, -135, -178, -145),
            "G7": (-52, -105, -178, -105),
            "G5": (-64, -25, -178, -65),
            "G4": (-66, 30, -178, -25),
            "SNIPER": (-80, 5, -178, 15),

            # Superiores y Rueda
            "LEFT": (-26, -165, -178, -185),
            "RIGHT": (26, -165, 76, -185),
            "MIDDLE": (0, -115, 76, -145),
            "WHEEL_LEFT": (-14, -115, -178, -145),
            "WHEEL_RIGHT": (14, -115, 76, -110),
            "G9": (0, -25, 76, -65),
        }

        # Ignorar WHEEL_LEFT separado en vista compacta para evitar saturación
        draw_keys = ["LEFT", "RIGHT", "MIDDLE", "G8", "G7", "G5", "G4", "SNIPER", "G9"]

        r_accent, g_accent, b_accent = (0.0, 0.898, 1.0)  # Cian de acento

        tag_w = 104
        tag_h = 24

        for btn_id in draw_keys:
            pin_x, pin_y, tag_x, tag_y = button_coords[btn_id]
            meta = BUTTON_METADATA.get(btn_id, {"name": btn_id})
            btn_name = meta["name"]
            action = assignments.get(btn_id)
            is_hovered = (self._hovered_button == btn_id)

            # 1. Punto de anclaje en el ratón
            cr.save()
            if is_hovered:
                cr.set_source_rgba(r_accent, g_accent, b_accent, 1.0)
                cr.arc(pin_x, pin_y, 5.5, 0, 2 * math.pi)
                cr.fill_preserve()
                cr.set_line_width(2.0)
                cr.set_source_rgba(1.0, 1.0, 1.0, 0.9)
                cr.stroke()
            else:
                cr.set_source_rgba(0.2, 0.25, 0.3, 0.85)
                cr.arc(pin_x, pin_y, 4.0, 0, 2 * math.pi)
                cr.fill_preserve()
                cr.set_line_width(1.2)
                cr.set_source_rgba(r_accent, g_accent, b_accent, 0.7)
                cr.stroke()
            cr.restore()

            # 2. Línea guía (Leader Line)
            cr.save()
            cr.set_line_width(1.2 if is_hovered else 0.8)
            if is_hovered:
                cr.set_source_rgba(r_accent, g_accent, b_accent, 0.9)
            else:
                cr.set_source_rgba(0.4, 0.5, 0.6, 0.45)

            # Conexión limpia al borde de la tarjeta
            connect_x = (tag_x + tag_w) if tag_x < 0 else tag_x
            mid_x = (pin_x + connect_x) * 0.5
            cr.move_to(pin_x, pin_y)
            cr.line_to(mid_x, tag_y + 12)
            cr.line_to(connect_x, tag_y + 12)
            cr.stroke()
            cr.restore()

            # 3. Etiqueta / Tarjeta de asignación
            box_x = tag_x

            # Registrar caja delimitadora para colisiones de clic y hover en coordenadas de ventana
            screen_x1 = cx + (box_x * scale)
            screen_y1 = cy + (tag_y * scale)
            screen_x2 = screen_x1 + (tag_w * scale)
            screen_y2 = screen_y1 + (tag_h * scale)
            self._hit_targets[btn_id] = (screen_x1, screen_y1, screen_x2, screen_y2)

            # Fondo de la tarjeta
            cr.save()
            cr.new_sub_path()
            radius = 4
            x, y, w, h = box_x, tag_y, tag_w, tag_h
            cr.arc(x + radius, y + radius, radius, math.pi, 1.5 * math.pi)
            cr.arc(x + w - radius, y + radius, radius, 1.5 * math.pi, 2 * math.pi)
            cr.arc(x + w - radius, y + h - radius, radius, 0, 0.5 * math.pi)
            cr.arc(x + radius, y + h - radius, radius, 0.5 * math.pi, math.pi)
            cr.close_path()

            if is_hovered:
                cr.set_source_rgba(0.0, 0.898, 1.0, 0.22)
                cr.fill_preserve()
                cr.set_line_width(1.2)
                cr.set_source_rgba(0.0, 0.898, 1.0, 0.9)
                cr.stroke()
            elif action:
                cr.set_source_rgba(0.12, 0.16, 0.22, 0.85)
                cr.fill_preserve()
                cr.set_line_width(0.8)
                cr.set_source_rgba(0.0, 0.898, 1.0, 0.4)
                cr.stroke()
            else:
                cr.set_source_rgba(0.11, 0.12, 0.14, 0.75)
                cr.fill_preserve()
                cr.set_line_width(0.6)
                cr.set_source_rgba(0.3, 0.35, 0.4, 0.3)
                cr.stroke()

            # Texto del botón
            cr.set_font_size(8.5)
            cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)

            # Título del botón (ej. G5 o SNIPER)
            if is_hovered:
                cr.set_source_rgb(0.0, 0.898, 1.0)
            else:
                cr.set_source_rgb(0.9, 0.92, 0.95)
            cr.move_to(box_x + 6, tag_y + 11)
            cr.show_text(btn_id)

            # Subtexto de acción o tecla
            cr.set_font_size(7.5)
            cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
            if action:
                cr.set_source_rgb(0.0, 0.898, 1.0)
                name_disp = action.name
                if len(name_disp) > 10:
                    name_disp = name_disp[:9] + "…"
                txt = f"[{action.binding_value}] {name_disp}"
            else:
                cr.set_source_rgba(0.6, 0.65, 0.7, 0.5)
                txt = "Sin asignar"

            cr.move_to(box_x + 6, tag_y + 20)
            cr.show_text(txt)
            cr.restore()

    # -------------------------------------------------------------------------
    # Manejo de Interacción y Eventos
    # -------------------------------------------------------------------------
    def _find_hit_button(self, x: float, y: float) -> str | None:
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
