"""
Pruebas unitarias para AutomationEngine.
"""

from pathlib import Path
import sys
import tempfile
import unittest

src_path = Path(__file__).resolve().parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from domain import Action, Button, DpiConfiguration, Profile
from engine import AutomationEngine
from services import ProfileManager
from storage import JsonProfileRepository


class DummyDeviceAdapter:
    """Adaptador de dispositivo simulado para pruebas de automatización."""

    def __init__(self):
        self.device_id = "test-g502"
        self.applied_profiles: list[Profile] = []
        self.switched_slots: list[int] = []

    def find_device(self, target_name: str = "Logitech G502 HERO Gaming Mouse") -> str | None:
        return self.device_id

    def switch_profile_slot(self, device: str, slot: int) -> bool:
        self.switched_slots.append(slot)
        return True

    def apply_profile(self, device: str, profile: Profile, slot: int | None = None) -> bool:
        self.applied_profiles.append(profile)
        return True


class TestAutomationEngine(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.file_path = Path(self.temp_dir.name) / "profiles.json"
        self.repo = JsonProfileRepository(self.file_path)
        self.manager = ProfileManager(self.repo)
        self.adapter = DummyDeviceAdapter()

        self.logs: list[str] = []
        self.engine = AutomationEngine(
            profile_manager=self.manager,
            device_adapter=self.adapter,
            check_interval=1.0,
            target_device_name="Logitech G502 HERO Gaming Mouse",
            desktop_profile_slot=0,
            logger=lambda msg: self.logs.append(msg),
        )

        # Crear perfil para Warframe
        self.wf_profile = self.manager.create_profile(
            name="Saryn DPS",
            application_id="steam:230410",
            dpi=1600,
            led_color="#00E5FF",
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_initialize_success(self):
        self.assertTrue(self.engine.initialize())
        self.assertEqual(self.engine._device_id, "test-g502")

    def test_restore_desktop(self):
        self.engine.initialize()
        self.engine.restore_desktop()
        self.assertIn(0, self.adapter.switched_slots)

    def test_restore_desktop_with_desktop_profile(self):
        self.engine.initialize()
        desk_prof = self.manager.create_profile(
            name="Escritorio / Navegación",
            application_id="desktop:general",
            dpi=1600,
            led_color="#00E5FF",
        )
        self.engine.restore_desktop()
        self.assertIn(desk_prof, self.adapter.applied_profiles)

    def test_stop_engine_sets_event_and_restores_desktop(self):
        self.engine.initialize()
        self.assertFalse(self.engine._stop_event.is_set())
        self.engine.stop()
        self.assertTrue(self.engine._stop_event.is_set())
        self.assertIn(0, self.adapter.switched_slots)

    def test_callbacks_on_profile_applied_and_desktop_restored(self):
        applied_events = []
        restored_events = []

        engine_with_callbacks = AutomationEngine(
            profile_manager=self.manager,
            device_adapter=self.adapter,
            check_interval=0.1,
            on_profile_applied=lambda app, prof: applied_events.append((app, prof)),
            on_desktop_restored=lambda: restored_events.append(True),
            logger=lambda msg: None,
        )
        engine_with_callbacks.initialize()

        # Al restaurar escritorio se llama al callback de restauración
        engine_with_callbacks.restore_desktop()
        self.assertEqual(len(restored_events), 1)


    def test_engine_detects_variant_and_battery(self):
        from domain import G502_VARIANTS

        class VariantBatteryAdapter(DummyDeviceAdapter):
            def detect_device_variant(self, device: str):
                return G502_VARIANTS["g502_lightspeed"]

            def get_cached_battery_level(self, device: str, ttl_seconds: float = 30.0):
                return 88

        bat_adapter = VariantBatteryAdapter()
        engine = AutomationEngine(
            profile_manager=self.manager,
            device_adapter=bat_adapter,
            check_interval=1.0,
            logger=lambda msg: self.logs.append(msg),
        )
        self.assertTrue(engine.initialize())
        self.assertEqual(engine.device_variant, G502_VARIANTS["g502_lightspeed"])
        self.assertEqual(engine.battery_level, 88)
        self.assertTrue(any("88%" in log for log in self.logs))


if __name__ == "__main__":
    unittest.main()
