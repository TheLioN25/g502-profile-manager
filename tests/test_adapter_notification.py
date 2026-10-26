"""
Pruebas unitarias para DesktopNotificationAdapter (OSD / Gaming Toast).
"""

from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import MagicMock

src_path = Path(__file__).resolve().parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from adapters.notification_adapter import DesktopNotificationAdapter
from domain import DpiConfiguration, Profile
from engine import AutomationEngine
from services import ProfileManager
from storage import JsonProfileRepository


class TestDesktopNotificationAdapter(unittest.TestCase):
    def test_disabled_notification_returns_false(self):
        adapter = DesktopNotificationAdapter(enabled=False)
        self.assertFalse(adapter.enabled)
        result = adapter.send_notification("Título", "Cuerpo")
        self.assertFalse(result)

    def test_custom_dbus_call_success(self):
        calls = []

        def mock_dbus(title, body, icon, timeout, sync_id):
            calls.append((title, body, icon, timeout, sync_id))
            return ("mock_id",)

        adapter = DesktopNotificationAdapter(enabled=True, dbus_call_sync=mock_dbus)
        res = adapter.send_notification("Alerta", "Mensaje de prueba", timeout_ms=1500)

        self.assertTrue(res)
        self.assertEqual(len(calls), 1)
        title, body, icon, timeout, sync_id = calls[0]
        self.assertEqual(title, "Alerta")
        self.assertEqual(body, "Mensaje de prueba")
        self.assertEqual(timeout, 1500)
        self.assertEqual(sync_id, "g502-profile-change")

    def test_fallback_to_notify_send_on_dbus_error(self):
        def failing_dbus(*_args):
            raise RuntimeError("D-Bus no disponible")

        runner_calls = []

        def mock_runner(cmd, **_kwargs):
            runner_calls.append(cmd)
            return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

        adapter = DesktopNotificationAdapter(
            enabled=True,
            dbus_call_sync=failing_dbus,
            command_runner=mock_runner,
        )
        res = adapter.send_notification("Título Fallback", "Cuerpo Fallback", timeout_ms=2000)

        self.assertTrue(res)
        self.assertEqual(len(runner_calls), 1)
        cmd = runner_calls[0]
        self.assertIn("notify-send", cmd[0])
        self.assertIn("Título Fallback", cmd)
        self.assertIn("Cuerpo Fallback", cmd)

    def test_notify_profile_switched_formatting(self):
        sent = []

        def mock_dbus(title, body, icon, timeout, sync_id):
            sent.append((title, body, timeout, sync_id))
            return ("id_123",)

        adapter = DesktopNotificationAdapter(enabled=True, dbus_call_sync=mock_dbus)
        res = adapter.notify_profile_switched(
            app_name="Warframe",
            profile_name="Saryn DPS",
            dpi=1200,
        )

        self.assertTrue(res)
        self.assertEqual(len(sent), 1)
        title, body, timeout, sync_id = sent[0]
        self.assertIn("Warframe", title)
        self.assertIn("Saryn DPS", body)
        self.assertIn("1,200 DPI", body)
        self.assertEqual(timeout, 1800)
        self.assertEqual(sync_id, "g502-profile-change")

    def test_notify_desktop_restored_formatting(self):
        sent = []

        def mock_dbus(title, body, icon, timeout, sync_id):
            sent.append((title, body, timeout, sync_id))
            return ("id_456",)

        adapter = DesktopNotificationAdapter(enabled=True, dbus_call_sync=mock_dbus)
        res = adapter.notify_desktop_restored(dpi=800)

        self.assertTrue(res)
        self.assertEqual(len(sent), 1)
        title, body, timeout, sync_id = sent[0]
        self.assertTrue("Desktop" in title or "Escritorio" in title)
        self.assertIn("800 DPI", body)
        self.assertEqual(timeout, 1500)

    def test_notification_debouncing_suppresses_rapid_duplicates(self):
        sent = []

        def mock_dbus(title, body, icon, timeout, sync_id):
            sent.append((title, body))
            return ("id_1",)

        adapter = DesktopNotificationAdapter(
            enabled=True, dbus_call_sync=mock_dbus, debounce_window_sec=3.0
        )
        res1 = adapter.notify_profile_switched(
            app_name="Warframe", profile_name="Saryn DPS", dpi=1200
        )
        res2 = adapter.notify_profile_switched(
            app_name="Warframe", profile_name="Saryn DPS", dpi=1200
        )

        self.assertTrue(res1)
        self.assertTrue(res2)
        # Solo se despachó 1 llamada física a D-Bus debido al debounce
        self.assertEqual(len(sent), 1)

    def test_notification_force_bypasses_debounce(self):
        sent = []

        def mock_dbus(title, body, icon, timeout, sync_id):
            sent.append((title, body))
            return ("id_2",)

        adapter = DesktopNotificationAdapter(
            enabled=True, dbus_call_sync=mock_dbus, debounce_window_sec=3.0
        )
        adapter.notify_profile_switched(
            app_name="Warframe", profile_name="Saryn DPS", dpi=1200
        )
        adapter.notify_profile_switched(
            app_name="Warframe", profile_name="Saryn DPS", dpi=1200, force=True
        )

        self.assertEqual(len(sent), 2)


class DummyDeviceAdapter:
    def __init__(self):
        self.device_id = "test-g502"
        self.applied_profiles: list[Profile] = []

    def find_device(self, target_name: str = "Logitech G502 HERO Gaming Mouse") -> str | None:
        return self.device_id

    def switch_profile_slot(self, device: str, slot: int) -> bool:
        return True

    def apply_profile(self, device: str, profile: Profile, slot: int | None = None, **kwargs) -> bool:
        self.applied_profiles.append(profile)
        return True

    def get_active_profile_slot(self, device: str) -> int | None:
        return 0


class DummyDiscoveryAdapter:
    def discover_all_applications(self):
        return ()


class TestEngineNotificationIntegration(unittest.TestCase):
    def test_engine_dispatches_notifications_on_profile_and_desktop(self):
        repo = MagicMock(spec=JsonProfileRepository)
        profile_wf = Profile(
            name="Excalibur",
            application_id="steam:warframe",
            dpi=DpiConfiguration(dpi=1600),
            profile_id="p-wf",
        )
        desktop_prof = Profile(
            name="Normal",
            application_id="desktop:general",
            dpi=DpiConfiguration(dpi=800),
            profile_id="p-desk",
        )

        def mock_get_profile(app_id):
            if app_id == "steam:warframe":
                return profile_wf
            if app_id == "desktop:general":
                return desktop_prof
            return None

        manager = MagicMock(spec=ProfileManager)
        manager.get_active_profile_for_application.side_effect = mock_get_profile

        notifications = []
        mock_notifier = MagicMock(spec=DesktopNotificationAdapter)
        mock_notifier.enabled = True
        mock_notifier.notify_profile_switched.side_effect = lambda app_name, profile_name, dpi, led_color=None: notifications.append(("switch", app_name, profile_name, dpi))
        mock_notifier.notify_desktop_restored.side_effect = lambda dpi=None: notifications.append(("restore", dpi))

        engine = AutomationEngine(
            profile_manager=manager,
            device_adapter=DummyDeviceAdapter(),
            discovery_adapter=DummyDiscoveryAdapter(),
            notification_adapter=mock_notifier,
            check_interval=0.1,
            logger=lambda _: None,
        )
        engine.initialize()

        # Simular aplicación de perfil
        from adapters.application_resolver import ActiveApplication
        active_app = ActiveApplication(
            name="Warframe",
            application_id="steam:warframe",
            source="steam",
            executable="Warframe.x64.exe",
            desktop_files=(),
            process_ids=(1234,),
            ambiguous=False,
        )
        with unittest.mock.patch("engine.discover_processes", return_value=[]), \
             unittest.mock.patch("engine.resolve_active_applications", return_value=[active_app]), \
             unittest.mock.patch("engine.combine_active_applications", return_value=[active_app]):
            engine.step()

        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0], ("switch", "Warframe", "Excalibur", 1600))

        # Simular vuelta al escritorio
        with unittest.mock.patch("engine.discover_processes", return_value=[]), \
             unittest.mock.patch("engine.combine_active_applications", return_value=[]):
            engine.step()

        self.assertEqual(len(notifications), 2)
        self.assertEqual(notifications[1], ("restore", 800))

    def test_engine_hardware_drift_does_not_spam_notification(self):
        repo = MagicMock(spec=JsonProfileRepository)
        profile_wf = Profile(
            name="Excalibur",
            application_id="steam:warframe",
            dpi=DpiConfiguration(dpi=1600),
            profile_id="p-wf",
        )
        manager = MagicMock(spec=ProfileManager)
        manager.get_active_profile_for_application.return_value = profile_wf

        notifications = []
        mock_notifier = MagicMock(spec=DesktopNotificationAdapter)
        mock_notifier.enabled = True
        mock_notifier.notify_profile_switched.side_effect = lambda app_name, profile_name, dpi, led_color=None: notifications.append(("switch", app_name, profile_name, dpi))

        # Dispositivo que simula deriva a slot 1 después de activarse
        current_slot_val = [0]
        class DriftingDeviceAdapter(DummyDeviceAdapter):
            def get_active_profile_slot(self, device: str) -> int | None:
                return current_slot_val[0]

        device_mock = DriftingDeviceAdapter()
        engine = AutomationEngine(
            profile_manager=manager,
            device_adapter=device_mock,
            discovery_adapter=DummyDiscoveryAdapter(),
            notification_adapter=mock_notifier,
            check_interval=0.1,
            logger=lambda _: None,
        )
        engine.initialize()

        from adapters.application_resolver import ActiveApplication
        active_app = ActiveApplication(
            name="Warframe",
            application_id="steam:warframe",
            source="steam",
            executable="Warframe.x64.exe",
            desktop_files=(),
            process_ids=(1234,),
            ambiguous=False,
        )
        with unittest.mock.patch("engine.discover_processes", return_value=[]), \
             unittest.mock.patch("engine.resolve_active_applications", return_value=[active_app]), \
             unittest.mock.patch("engine.combine_active_applications", return_value=[active_app]):
            # 1. Primer ciclo: activación de perfil (debe notificar una única vez)
            engine.step()
            self.assertEqual(len(notifications), 1)

            # 2. Simular deriva de hardware en el ratón (slot cambió a 1 físicamente)
            current_slot_val[0] = 1

            # Segundo ciclo: debe detectar la deriva, aplicar corrección, pero NO spamear notificación
            engine.step()
            self.assertEqual(len(notifications), 1)

            # Tercer ciclo con deriva todavía en 1: sigue sin notificar
            engine.step()
            self.assertEqual(len(notifications), 1)
