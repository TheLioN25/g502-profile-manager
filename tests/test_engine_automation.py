"""
Pruebas unitarias para AutomationEngine.
"""

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

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

    def apply_profile(self, device: str, profile: Profile, slot: int | None = None, **kwargs) -> bool:
        self.applied_profiles.append(profile)
        return True

    def get_active_profile_slot(self, device: str) -> int | None:
        return 0


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

    def test_apply_failure_backoff_throttles_retries(self):
        class FailingApplyAdapter(DummyDeviceAdapter):
            def __init__(self):
                super().__init__()
                self.apply_call_count = 0

            def apply_profile(self, device: str, profile: Profile, **kwargs) -> bool:
                self.apply_call_count += 1
                return False

        failing_adapter = FailingApplyAdapter()
        engine = AutomationEngine(
            profile_manager=self.manager,
            device_adapter=failing_adapter,
            check_interval=0.1,
            logger=lambda _: None,
        )
        engine.initialize()

        from adapters.application_resolver import ActiveApplication
        game_app = ActiveApplication(
            name="Game Test",
            application_id=self.wf_profile.application_id,
            source="steam",
            executable="game.exe",
            desktop_files=(),
            process_ids=(999,),
            ambiguous=False,
        )

        with patch("engine.discover_processes", return_value=[]), \
             patch("engine.resolve_active_applications", return_value=[game_app]), \
             patch("engine.combine_active_applications", return_value=[game_app]):
            # 1. Primer ciclo: debe intentar aplicar y registrar el fallo
            engine.step()
            self.assertEqual(failing_adapter.apply_call_count, 1)
            self.assertEqual(engine._apply_failures, 1)

            # 2. Ciclos subsiguientes inmediatos: deben ser ignorados por el backoff
            engine.step()
            engine.step()
            self.assertEqual(failing_adapter.apply_call_count, 1)

            # 3. Al vencer la ventana de backoff, debe reintentar
            engine._next_apply_attempt = 0.0
            engine.step()
            self.assertEqual(failing_adapter.apply_call_count, 2)
            self.assertEqual(engine._apply_failures, 2)

    def test_apply_failure_backoff_isolated_by_target(self):
        class FailingApplyAdapter(DummyDeviceAdapter):
            def __init__(self):
                super().__init__()
                self.apply_call_count = 0

            def apply_profile(self, device: str, profile: Profile, **kwargs) -> bool:
                self.apply_call_count += 1
                return False

            def switch_profile_slot(self, device: str, slot: int) -> bool:
                return False

        failing_adapter = FailingApplyAdapter()
        engine = AutomationEngine(
            profile_manager=self.manager,
            device_adapter=failing_adapter,
            check_interval=0.1,
            logger=lambda _: None,
        )
        engine.initialize()
        engine._current_profile_id = self.wf_profile.id

        # Simular fallo en desktop
        engine._register_apply_failure("desktop", "escritorio")
        self.assertEqual(engine._apply_failure_target, "desktop")

        # Un perfil de juego diferente no debe heredar el backoff de desktop
        from adapters.application_resolver import ActiveApplication
        game_app = ActiveApplication(
            name="Game Test",
            application_id=self.wf_profile.application_id,
            source="steam",
            executable="game.exe",
            desktop_files=(),
            process_ids=(999,),
            ambiguous=False,
        )
        with patch("engine.discover_processes", return_value=[]), \
             patch("engine.resolve_active_applications", return_value=[game_app]), \
             patch("engine.combine_active_applications", return_value=[game_app]):
            engine.step()
            # Debe haber intentado aplicar el juego porque el target cambió
            self.assertEqual(failing_adapter.apply_call_count, 1)
            self.assertEqual(engine._apply_failure_target, self.wf_profile.id)


if __name__ == "__main__":
    unittest.main()
