"""
Pruebas unitarias para JsonProfileRepository.
"""

import sys
import tempfile
from pathlib import Path
import unittest

src_path = Path(__file__).resolve().parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from domain import Action, Button, DpiConfiguration, Profile
from storage import JsonProfileRepository



def _multiprocess_worker(file_path_str: str, proc_idx: int, count: int, barrier, err_queue):
    from pathlib import Path
    from domain import Profile
    from storage.profile_repository import JsonProfileRepository

    try:
        barrier.wait()
        repo = JsonProfileRepository(Path(file_path_str))
        for i in range(count):
            p = Profile(
                name=f"Proc {proc_idx} Prof {i}",
                application_id="test:concurrency",
                dpi=1000 + proc_idx * 100 + i,
                profile_id=f"p-proc-{proc_idx}-{i}",
            )
            repo.save(p)
    except Exception as e:
        err_queue.put(f"Proc {proc_idx} error: {e}")

class TestJsonProfileRepository(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.file_path = Path(self.temp_dir.name) / "profiles.json"
        self.repo = JsonProfileRepository(self.file_path)

        self.app_id = "steam:230410"
        self.profile = Profile(
            name="Saryn DPS",
            application_id=self.app_id,
            dpi=DpiConfiguration(1600, shift_dpi=400),
            led_color="#00E5FF",
            profile_id="p-1234",
        )
        self.btn_g5 = Button("G5", "G5 Button")
        self.action_1 = Action(
            "habilidad_1",
            "Habilidad 1",
            self.app_id,
            binding_type="key",
            binding_value="1",
        )
        self.profile.assign(self.btn_g5, self.action_1)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_save_and_retrieve_profile(self):
        self.repo.save(self.profile)

        retrieved = self.repo.get_by_id("p-1234")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "Saryn DPS")
        self.assertEqual(retrieved.application_id, self.app_id)
        self.assertEqual(retrieved.dpi.dpi, 1600)
        self.assertEqual(retrieved.dpi.shift_dpi, 400)
        self.assertEqual(retrieved.led_color, "#00E5FF")
        self.assertEqual(retrieved.led_mode, "on")
        self.assertIsNone(retrieved.led_duration)
        self.assertIsNotNone(retrieved.created_at)
        self.assertIsNotNone(retrieved.updated_at)
        self.assertEqual(len(retrieved.list_assignments()), 1)

        assignment = retrieved.get_assignment_for_button(self.btn_g5)
        self.assertIsNotNone(assignment)
        self.assertEqual(assignment.button.button_id, "G5")
        self.assertEqual(assignment.action.action_id, "habilidad_1")
        self.assertEqual(assignment.action.binding_type, "key")
        self.assertEqual(assignment.action.binding_value, "1")

    def test_save_and_retrieve_custom_led_mode(self):
        p_breathe = Profile(
            name="Breathing RGB",
            application_id=self.app_id,
            dpi=DpiConfiguration(2400),
            led_color="#5500DD",
            led_mode="breathing",
            led_duration=3000,
            profile_id="p-breathe",
        )
        self.repo.save(p_breathe)

        loaded = self.repo.get_by_id("p-breathe")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.led_mode, "breathing")
        self.assertEqual(loaded.led_duration, 3000)
        self.assertEqual(loaded.led_color, "#5500DD")


    def test_persistence_across_instances(self):
        """Comprueba que una nueva instancia cargue exactamente los datos guardados en disco."""
        self.repo.save(self.profile)

        new_repo = JsonProfileRepository(self.file_path)
        retrieved = new_repo.get_by_id("p-1234")

        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "Saryn DPS")
        self.assertEqual(len(retrieved.list_assignments()), 1)

    def test_get_by_application(self):
        p2 = Profile(
            name="Mesa Peacemaker",
            application_id=self.app_id,
            dpi=800,
            profile_id="p-5678",
        )
        p_other = Profile(
            name="Blender General",
            application_id="desktop:blender",
            dpi=1000,
            profile_id="p-9999",
        )
        self.repo.save(self.profile)
        self.repo.save(p2)
        self.repo.save(p_other)

        wf_profiles = self.repo.get_by_application(self.app_id)
        self.assertEqual(len(wf_profiles), 2)
        ids = {p.id for p in wf_profiles}
        self.assertEqual(ids, {"p-1234", "p-5678"})

    def test_default_profile_management(self):
        self.repo.save(self.profile)
        self.assertIsNone(self.repo.get_default_profile_id(self.app_id))

        self.repo.set_default_profile_id(self.app_id, "p-1234")
        self.assertEqual(self.repo.get_default_profile_id(self.app_id), "p-1234")

        # Comprobar persistencia del default en nueva instancia
        new_repo = JsonProfileRepository(self.file_path)
        self.assertEqual(new_repo.get_default_profile_id(self.app_id), "p-1234")

    def test_set_default_profile_non_existent_fails(self):
        with self.assertRaises(ValueError):
            self.repo.set_default_profile_id(self.app_id, "inexistente")

    def test_set_default_profile_wrong_application_fails(self):
        p_blender = Profile(
            name="Blender",
            application_id="desktop:blender",
            profile_id="p-blender",
        )
        self.repo.save(p_blender)

        with self.assertRaises(ValueError):
            self.repo.set_default_profile_id(self.app_id, "p-blender")

    def test_dynamic_reload_on_external_modification(self):
        self.repo.save(self.profile)

        # Simular otro proceso modificando el archivo JSON externamente
        other_repo = JsonProfileRepository(self.file_path)
        external_profile = Profile(
            name="External Update",
            application_id=self.app_id,
            dpi=1600,
            profile_id="p-ext-99",
        )
        other_repo.save(external_profile)

        # La instancia original self.repo debe detectar el cambio y recargar
        fetched = self.repo.get_by_id("p-ext-99")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.name, "External Update")


    def test_delete_profile_removes_from_repository_and_default(self):
        self.repo.save(self.profile)
        self.repo.set_default_profile_id(self.app_id, self.profile.id)
        self.assertEqual(self.repo.get_default_profile_id(self.app_id), self.profile.id)

        # Eliminar
        deleted = self.repo.delete(self.profile.id)
        self.assertTrue(deleted)
        self.assertIsNone(self.repo.get_by_id(self.profile.id))
        self.assertIsNone(self.repo.get_default_profile_id(self.app_id))

        # Intentar eliminar de nuevo debe retornar False
        self.assertFalse(self.repo.delete(self.profile.id))
        self.assertFalse(self.repo.delete("id_inexistente"))


    def test_corrupt_file_is_preserved_and_reported(self):
        corrupt_path = Path(self.temp_dir.name) / "corrupted_profiles.json"
        raw_bytes = b"{\n  this is definitely invalid json content\n"
        corrupt_path.write_bytes(raw_bytes)

        from storage.profile_repository import CorruptedProfileRepositoryError
        repo = JsonProfileRepository(corrupt_path)

        self.assertTrue(repo.is_corrupted)
        self.assertIsNotNone(repo.corrupt_backup_path)
        self.assertTrue(repo.corrupt_backup_path.exists())
        self.assertEqual(repo.corrupt_backup_path.read_bytes(), raw_bytes)

        # save() debe lanzar CorruptedProfileRepositoryError y no pisar el archivo corrupto
        new_prof = Profile(name="New", application_id="test:app", dpi=800, profile_id="p-safe")
        with self.assertRaises(CorruptedProfileRepositoryError):
            repo.save(new_prof)

        # El archivo original sigue intacto
        self.assertEqual(corrupt_path.read_bytes(), raw_bytes)

    def test_concurrent_save_and_list(self):
        import threading

        num_threads = 5
        profiles_per_thread = 5
        errors = []

        def worker(thread_idx: int):
            try:
                for i in range(profiles_per_thread):
                    p = Profile(
                        name=f"Prof {thread_idx}-{i}",
                        application_id=self.app_id,
                        dpi=1000 + thread_idx * 10 + i,
                        profile_id=f"p-th-{thread_idx}-{i}",
                    )
                    self.repo.save(p)
                    # Lectura concurrente
                    all_p = self.repo.list_all()
                    self.assertTrue(len(all_p) > 0)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Errores concurrentes: {errors}")
        all_saved = self.repo.list_all()
        self.assertEqual(len(all_saved), num_threads * profiles_per_thread)

    def test_multiprocess_concurrent_save_with_barrier(self):
        import multiprocessing
        file_path = Path(self.temp_dir.name) / "mp_profiles.json"
        # Inicializar repositorio limpio
        repo = JsonProfileRepository(file_path)

        num_procs = 3
        profiles_per_proc = 20
        barrier = multiprocessing.Barrier(num_procs)
        err_queue = multiprocessing.Queue()

        processes = []
        for p_idx in range(num_procs):
            proc = multiprocessing.Process(
                target=_multiprocess_worker,
                args=(str(file_path), p_idx, profiles_per_proc, barrier, err_queue),
            )
            processes.append(proc)
            proc.start()

        for proc in processes:
            proc.join(timeout=10)

        errors = []
        while not err_queue.empty():
            errors.append(err_queue.get())
        self.assertEqual(len(errors), 0, f"Errores en procesos concurrentes: {errors}")

        final_repo = JsonProfileRepository(file_path)
        all_saved = final_repo.list_all()
        self.assertEqual(len(all_saved), num_procs * profiles_per_proc)

    def test_file_lock_failure_raises_profile_lock_error(self):
        from storage.profile_repository import ProfileLockError
        lock_path = self.file_path.with_name(f"{self.file_path.name}.lock")
        # Simular fallo creando un directorio con el nombre del lockfile para impedir open()
        lock_path.mkdir(parents=True, exist_ok=True)
        try:
            p = Profile(name="LockFail", application_id="test:app", dpi=800, profile_id="p-lock")
            with self.assertRaises(ProfileLockError):
                self.repo.save(p)
        finally:
            if lock_path.is_dir():
                lock_path.rmdir()

    def test_corrupt_file_does_not_mutate_in_memory_profiles(self):
        corrupt_path = Path(self.temp_dir.name) / "corrupt_nomutate.json"
        corrupt_path.write_bytes(b"INVALID JSON CONTENT")
        from storage.profile_repository import CorruptedProfileRepositoryError
        repo = JsonProfileRepository(corrupt_path)

        self.assertTrue(repo.is_corrupted)
        self.assertEqual(len(repo.list_all()), 0)

        p = Profile(name="NoMutate", application_id="test:app", dpi=800, profile_id="p-nomutate")
        with self.assertRaises(CorruptedProfileRepositoryError):
            repo.save(p)

        self.assertEqual(len(repo.list_all()), 0)
        self.assertIsNone(repo.get_by_id("p-nomutate"))

    def test_save_rollback_on_io_error(self):
        from unittest.mock import patch
        p = Profile(name="RollbackTest", application_id="test:app", dpi=800, profile_id="p-rollback")
        
        with patch.object(self.repo, "_flush", side_effect=OSError("Disk full")):
            with self.assertRaises(OSError):
                self.repo.save(p)
                
        # Verificar que el perfil no quedó en memoria
        self.assertIsNone(self.repo.get_by_id("p-rollback"))

    def test_delete_rollback_on_io_error(self):
        from unittest.mock import patch
        p = Profile(name="DelRollback", application_id="test:app", dpi=800, profile_id="p-del-roll")
        self.repo.save(p)
        self.repo.set_default_profile_id("test:app", p.id)

        with patch.object(self.repo, "_flush", side_effect=OSError("Disk full")):
            with self.assertRaises(OSError):
                self.repo.delete(p.id)

        self.assertIsNotNone(self.repo.get_by_id(p.id))
        self.assertEqual(self.repo.get_default_profile_id("test:app"), p.id)

    def test_set_default_rollback_on_io_error(self):
        from unittest.mock import patch
        p1 = Profile(name="P1", application_id="test:app", dpi=800, profile_id="p-1")
        p2 = Profile(name="P2", application_id="test:app", dpi=800, profile_id="p-2")
        self.repo.save(p1)
        self.repo.save(p2)
        self.repo.set_default_profile_id("test:app", p1.id)

        with patch.object(self.repo, "_flush", side_effect=OSError("Disk full")):
            with self.assertRaises(OSError):
                self.repo.set_default_profile_id("test:app", p2.id)

        self.assertEqual(self.repo.get_default_profile_id("test:app"), p1.id)




if __name__ == "__main__":
    unittest.main()

