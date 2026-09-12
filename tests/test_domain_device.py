"""
Pruebas unitarias para la entidad Device y Button.
"""

import sys
from pathlib import Path
import unittest

src_path = Path(__file__).resolve().parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from domain import Button, Device


class TestDomainDevice(unittest.TestCase):
    def test_valid_device_creation(self):
        dev = Device(device_id="logitech:g502", name="Logitech G502 HERO")
        self.assertEqual(dev.device_id, "logitech:g502")
        self.assertEqual(dev.name, "Logitech G502 HERO")
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


if __name__ == "__main__":
    unittest.main()
