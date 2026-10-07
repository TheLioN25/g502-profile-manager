"""
Pruebas unitarias para la entidad Device, Button, DeviceCapabilities y DeviceVariant.
"""

import sys
from pathlib import Path
import unittest

src_path = Path(__file__).resolve().parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from domain import (
    Button,
    Device,
    DeviceCapabilities,
    DeviceVariant,
    G502_VARIANTS,
    DEFAULT_VARIANT,
    get_variant_by_key,
)


class TestDomainDevice(unittest.TestCase):
    def test_valid_device_creation(self):
        dev = Device(device_id="logitech:g502", name="Logitech G502 HERO")
        self.assertEqual(dev.device_id, "logitech:g502")
        self.assertEqual(dev.name, "Logitech G502 HERO")
        self.assertEqual(dev.variant, DEFAULT_VARIANT)
        self.assertEqual(len(dev.list_buttons()), 0)

    def test_invalid_device_raises_error(self):
        with self.assertRaises(ValueError):
            Device(device_id="", name="G502")
        with self.assertRaises(ValueError):
            Device(device_id="g502", name="   ")

    def test_device_with_initial_buttons(self):
        btn1 = Button(button_id="LEFT", name="Click Izquierdo")
        btn2 = Button(button_id="RIGHT", name="Click Derecho")
        dev = Device(
            device_id="logitech:g502",
            name="Logitech G502",
            buttons=[btn1, btn2],
        )
        self.assertEqual(len(dev.list_buttons()), 2)
        self.assertEqual(dev.get_button("LEFT"), btn1)
        self.assertEqual(dev.get_button("RIGHT"), btn2)

    def test_add_button(self):
        dev = Device(device_id="logitech:g502", name="Logitech G502")
        btn = Button(button_id="G5", name="Botón G5")
        dev.add_button(btn)

        self.assertEqual(dev.get_button("G5"), btn)
        self.assertIsNone(dev.get_button("UNKNOWN"))

    def test_add_invalid_button_raises_error(self):
        dev = Device(device_id="mouse", name="Mouse")
        with self.assertRaises(TypeError):
            dev.add_button("no_es_un_boton")  # type: ignore

    def test_device_capabilities_validation(self):
        caps = DeviceCapabilities(max_dpi=12000, has_lighting=True, led_zones=1, has_rgb=False, has_battery=False)
        self.assertEqual(caps.max_dpi, 12000)
        self.assertFalse(caps.has_rgb)
        self.assertFalse(caps.has_battery)

        with self.assertRaises(ValueError):
            DeviceCapabilities(max_dpi=0)
        with self.assertRaises(ValueError):
            DeviceCapabilities(led_zones=-1)

    def test_device_variant_validation(self):
        caps = DeviceCapabilities()
        with self.assertRaises(ValueError):
            DeviceVariant(key="", name="Nombre", short_name="Corto", capabilities=caps)
        with self.assertRaises(ValueError):
            DeviceVariant(key="key", name="", short_name="Corto", capabilities=caps)
        with self.assertRaises(ValueError):
            DeviceVariant(key="key", name="Nombre", short_name="   ", capabilities=caps)

    def test_g502_variants_catalog(self):
        expected_keys = {
            "g502_proteus_core",
            "g502_proteus_spectrum",
            "g502_hero",
            "g502_lightspeed",
            "g502_x",
            "g502_x_wireless",
        }
        self.assertEqual(set(G502_VARIANTS.keys()), expected_keys)

        # Proteus Core: 12.000 DPI, 1 zona azul, sin batería
        core = G502_VARIANTS["g502_proteus_core"]
        self.assertEqual(core.capabilities.max_dpi, 12000)
        self.assertEqual(core.capabilities.led_zones, 1)
        self.assertFalse(core.capabilities.has_rgb)
        self.assertFalse(core.capabilities.has_battery)

        # Proteus Spectrum: 12.000 DPI, 2 zonas RGB, sin batería
        spectrum = G502_VARIANTS["g502_proteus_spectrum"]
        self.assertEqual(spectrum.capabilities.max_dpi, 12000)
        self.assertEqual(spectrum.capabilities.led_zones, 2)
        self.assertTrue(spectrum.capabilities.has_rgb)
        self.assertFalse(spectrum.capabilities.has_battery)

        # HERO: 25.600 DPI, 2 zonas RGB, sin batería
        hero = G502_VARIANTS["g502_hero"]
        self.assertEqual(hero.capabilities.max_dpi, 25600)
        self.assertEqual(hero.capabilities.led_zones, 2)
        self.assertTrue(hero.capabilities.has_rgb)
        self.assertFalse(hero.capabilities.has_battery)

        # LIGHTSPEED: 25.600 DPI, 2 zonas RGB, CON batería
        lightspeed = G502_VARIANTS["g502_lightspeed"]
        self.assertEqual(lightspeed.capabilities.max_dpi, 25600)
        self.assertTrue(lightspeed.capabilities.has_battery)

        # G502 X: 25.600 DPI, SIN iluminación RGB
        x = G502_VARIANTS["g502_x"]
        self.assertEqual(x.capabilities.max_dpi, 25600)
        self.assertFalse(x.capabilities.has_lighting)
        self.assertEqual(x.capabilities.led_zones, 0)
        self.assertFalse(x.capabilities.has_rgb)

        # G502 X Wireless / PLUS: 25.600 DPI, 8 zonas Lightform RGB, CON batería
        x_plus = G502_VARIANTS["g502_x_wireless"]
        self.assertEqual(x_plus.capabilities.max_dpi, 25600)
        self.assertTrue(x_plus.capabilities.has_lighting)
        self.assertEqual(x_plus.capabilities.led_zones, 8)
        self.assertTrue(x_plus.capabilities.has_battery)

    def test_get_variant_by_key(self):
        self.assertEqual(get_variant_by_key("g502_hero"), G502_VARIANTS["g502_hero"])
        self.assertEqual(get_variant_by_key("G502_LIGHTSPEED"), G502_VARIANTS["g502_lightspeed"])
        self.assertEqual(get_variant_by_key("g502_x"), G502_VARIANTS["g502_x"])
        # Fallback a HERO si la key es desconocida
        self.assertEqual(get_variant_by_key("inexistente"), DEFAULT_VARIANT)
        self.assertEqual(get_variant_by_key(""), DEFAULT_VARIANT)

    def test_device_custom_variant(self):
        core_variant = G502_VARIANTS["g502_proteus_core"]
        dev = Device(
            device_id="logitech:g502_core",
            name="Logitech G502 Proteus Core",
            variant=core_variant,
        )
        self.assertEqual(dev.variant, core_variant)
        self.assertEqual(dev.variant.capabilities.max_dpi, 12000)


if __name__ == "__main__":
    unittest.main()
