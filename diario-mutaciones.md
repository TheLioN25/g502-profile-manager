# 📔 Diario de Pruebas Mutantes — g502-profile-manager

**Fecha del escaneo:** 2026-11-16 23:35:42  
**Ruta del proyecto:** `/home/thelion/SSD/Proyectos/g502-profile-manager`  
**Total módulos analizados:** 28  
**Módulos 100% blindados:** 8  
**Módulos con deuda de mutación:** 20  
**Score global de mutación:** 43.9% (47/107 mutantes eliminados)

---

## 🟢 Módulos Blindados (100% Mutantes Eliminados)
- [x] `src/adapters/__init__.py` (Sin operadores de mutación aplicables)
- [x] `src/adapters/action_presets.py` (Sin operadores de mutación aplicables)
- [x] `src/adapters/application_resolver.py` (5/5 eliminados)
- [x] `src/domain/__init__.py` (Sin operadores de mutación aplicables)
- [x] `src/engine.py` (5/5 eliminados)
- [x] `src/gui/__init__.py` (Sin operadores de mutación aplicables)
- [x] `src/services/__init__.py` (Sin operadores de mutación aplicables)
- [x] `src/storage/__init__.py` (Sin operadores de mutación aplicables)

---

## 🔴 Módulos con Puntos Ciegos (Pendientes de Blindaje)
### ~~1. `src/adapters/application_discovery_adapter.py`~~ ✅ BLINDADO (Score: 40% → 100% — 3/3 eliminados)
> Resuelto en commit `2d07037` — Tests: `test_discover_steam_guard_skips_default_reader_when_file_missing`, aserción `is_game` en Steam, `test_discover_epic_applications_mocked`.

### ~~2. `src/adapters/desktop_entries.py`~~ ✅ BLINDADO (Score: 0% → 100% — 3/3 eliminados)
> Resuelto en commit `d958ae6` — Tests: inmutabilidad `DesktopEntry`, default `is_game=False`, `extract_exec_name` con inputs vacío/malformado/solo-env.

### ~~3. `src/adapters/epic_discovery.py`~~ ✅ BLINDADO (Score: 80.0% → 100% — 3/3 eliminados)
> Resuelto — Tests: `test_discover_lutris_epic_apps_mocked` (aniquilación de M-01 verificando SQLite `uri=True` / `mode=ro` y mapeo de juegos Epic) y `test_discover_lutris_epic_apps_missing_db`.

### ~~4. `src/adapters/notification_adapter.py`~~ ✅ BLINDADO (Score: 60.0% → 100% — 3/3 eliminados)
> Resuelto — Tests: `test_default_initialization` (aniquilación de M-01 validando default `enabled=True` y M-02 validando `_dbus_init_attempted=False`) y `test_dbus_init_attempted_transition_on_first_call`.

### ~~5. `src/adapters/process_discovery.py`~~ ✅ BLINDADO (Score: 0.0% → 100% — 3/3 eliminados)
> Resuelto — Suite unitaria dedicada `tests/test_adapter_process_discovery.py` (13 tests): inmutabilidad de `ProcessInfo` (M-01), parsing estricto de `cmdline` con y sin terminador nulo sin pop erróneo (M-02, M-03), retorno `None` ante `cmdline` vacío (M-04), y manejo seguro de `/proc` volátil / errores de E/S retornando `None` (M-05).

### ~~6. `src/adapters/ratbag_adapter.py`~~ ✅ BLINDADO (Score: 0.0% → 100% — 3/3 eliminados)
> Resuelto — Tests: `test_default_command_runner` (aniquilación de M-01 `capture_output=True`, M-02 `text=True` y M-03 `check=False`), `test_load_state_cache_with_none_file` (M-04 validando cortocircuito `or`), y `test_load_state_cache_parses_profile_slots_correctly` (M-05 validando procesamiento de ranuras y filtro `s_key == 'active_slot'`).

### ~~7. `src/adapters/steam_discovery.py`~~ ✅ BLINDADO (Score: 20.0% → 100% — 3/3 eliminados)
> Resuelto — Test: `test_steam_dataclasses_are_immutable` (aniquilación de M-01 `SteamLaunch`, M-02 `SteamAppManifest`, M-03 `ActiveSteamApplication` y M-04 `SteamShortcut` validando inmutabilidad con `FrozenInstanceError`).

### ~~8. `src/cli.py`~~ ✅ BLINDADO (Score: 0.0% → 100% — 3/3 eliminados)
> Resuelto — Suite unitaria dedicada `tests/test_cli_commands.py` (5 tests): `test_cli_bootstraps_sys_path` (M-01), `test_cmd_profiles_empty_repository_hint` (M-02, M-03), `test_cmd_profiles_default_tag_accuracy` (M-04), `test_cmd_presets_branching_list_vs_detail` (M-05) y `test_cmd_create_success`.

### 9. `src/domain/application.py` (Score: 60.0% — 2 superviviente(s))
* **[M-01] Línea 11:** Inversión booleana (True por False)
  * **Original:** `@dataclass(frozen=True)`
  * **Mutado:**   `@dataclass(frozen=False)`
  * **Diagnóstico:** La suite de pruebas no detectó esta mutación. Se requiere una aserción unitaria que verifique esta bifurcación.
* **[M-02] Línea 42:** Inversión lógica (and por or)
  * **Original:** `if isinstance(self.binding_type, str) and self.binding_type.strip()`
  * **Mutado:**   `if isinstance(self.binding_type, str) or self.binding_type.strip()`
  * **Diagnóstico:** La suite de pruebas no detectó esta mutación. Se requiere una aserción unitaria que verifique esta bifurcación.

### 10. `src/domain/device.py` (Score: 20.0% — 4 superviviente(s))
* **[M-01] Línea 11:** Inversión booleana (True por False)
  * **Original:** `@dataclass(frozen=True)`
  * **Mutado:**   `@dataclass(frozen=False)`
  * **Diagnóstico:** La suite de pruebas no detectó esta mutación. Se requiere una aserción unitaria que verifique esta bifurcación.
* **[M-02] Línea 20:** Inversión booleana (True por False)
  * **Original:** `has_lighting: bool = True`
  * **Mutado:**   `has_lighting: bool = False`
  * **Diagnóstico:** La suite de pruebas no detectó esta mutación. Se requiere una aserción unitaria que verifique esta bifurcación.
* **[M-03] Línea 22:** Inversión booleana (True por False)
  * **Original:** `has_rgb: bool = True`
  * **Mutado:**   `has_rgb: bool = False`
  * **Diagnóstico:** La suite de pruebas no detectó esta mutación. Se requiere una aserción unitaria que verifique esta bifurcación.
* **[M-04] Línea 23:** Inversión booleana (False por True)
  * **Original:** `has_battery: bool = False`
  * **Mutado:**   `has_battery: bool = True`
  * **Diagnóstico:** La suite de pruebas no detectó esta mutación. Se requiere una aserción unitaria que verifique esta bifurcación.

### 11. `src/domain/profile.py` (Score: 80.0% — 1 superviviente(s))
* **[M-01] Línea 19:** Inversión booleana (True por False)
  * **Original:** `@dataclass(frozen=True)`
  * **Mutado:**   `@dataclass(frozen=False)`
  * **Diagnóstico:** La suite de pruebas no detectó esta mutación. Se requiere una aserción unitaria que verifique esta bifurcación.

### 12. `src/gui/app.py` (Score: 50.0% — 1 superviviente(s))
* **[M-01] Línea 109:** Inversión booleana (True por False)
  * **Original:** `start_auto=True,`
  * **Mutado:**   `start_auto=False,`
  * **Diagnóstico:** La suite de pruebas no detectó esta mutación. Se requiere una aserción unitaria que verifique esta bifurcación.

### 13. `src/gui/dialogs.py` (Score: 0.0% — 5 superviviente(s))
* **[M-01] Línea 39:** Inversión booleana (True por False)
  * **Original:** `modal=True,`
  * **Mutado:**   `modal=False,`
  * **Diagnóstico:** La suite de pruebas no detectó esta mutación. Se requiere una aserción unitaria que verifique esta bifurcación.
* **[M-02] Línea 78:** Inversión booleana (True por False)
  * **Original:** `self._search_entry.set_hexpand(True)`
  * **Mutado:**   `self._search_entry.set_hexpand(False)`
  * **Diagnóstico:** La suite de pruebas no detectó esta mutación. Se requiere una aserción unitaria que verifique esta bifurcación.
* **[M-03] Línea 85:** Inversión booleana (True por False)
  * **Original:** `scrolled.set_vexpand(True)`
  * **Mutado:**   `scrolled.set_vexpand(False)`
  * **Diagnóstico:** La suite de pruebas no detectó esta mutación. Se requiere una aserción unitaria que verifique esta bifurcación.
* **[M-04] Línea 86:** Inversión booleana (True por False)
  * **Original:** `scrolled.set_hexpand(True)`
  * **Mutado:**   `scrolled.set_hexpand(False)`
  * **Diagnóstico:** La suite de pruebas no detectó esta mutación. Se requiere una aserción unitaria que verifique esta bifurcación.
* **[M-05] Línea 146:** Inversión booleana (True por False)
  * **Original:** `row.set_activatable(True)`
  * **Mutado:**   `row.set_activatable(False)`
  * **Diagnóstico:** La suite de pruebas no detectó esta mutación. Se requiere una aserción unitaria que verifique esta bifurcación.

### 14. `src/gui/mouse_diagram.py` (Score: 40.0% — 3 superviviente(s))
* **[M-01] Línea 49:** Inversión booleana (False por True)
  * **Original:** `self.set_hexpand(False)`
  * **Mutado:**   `self.set_hexpand(True)`
  * **Diagnóstico:** La suite de pruebas no detectó esta mutación. Se requiere una aserción unitaria que verifique esta bifurcación.
* **[M-02] Línea 50:** Inversión booleana (True por False)
  * **Original:** `self.set_vexpand(True)`
  * **Mutado:**   `self.set_vexpand(False)`
  * **Diagnóstico:** La suite de pruebas no detectó esta mutación. Se requiere una aserción unitaria que verifique esta bifurcación.
* **[M-03] Línea 84:** Inversión de igualdad (== por !=)
  * **Original:** `if len(clean) == 6:`
  * **Mutado:**   `if len(clean) != 6:`
  * **Diagnóstico:** La suite de pruebas no detectó esta mutación. Se requiere una aserción unitaria que verifique esta bifurcación.

### 15. `src/gui/tray.py` (Score: 80.0% — 1 superviviente(s))
* **[M-01] Línea 23:** Inversión menor estricto (< por >)
  * **Original:** `<property name="Category" type="s" access="read"/>`
  * **Mutado:**   `>property name="Category" type="s" access="read"/>`
  * **Diagnóstico:** La suite de pruebas no detectó esta mutación. Se requiere una aserción unitaria que verifique esta bifurcación.

### 16. `src/gui/window.py` (Score: 80.0% — 1 superviviente(s))
* **[M-01] Línea 111:** Inversión booleana (True por False)
  * **Original:** `initial_notif = True`
  * **Mutado:**   `initial_notif = False`
  * **Diagnóstico:** La suite de pruebas no detectó esta mutación. Se requiere una aserción unitaria que verifique esta bifurcación.

### 17. `src/i18n.py` (Score: 20.0% — 4 superviviente(s))
* **[M-01] Línea 39:** Inversión lógica (or por and)
  * **Original:** `"Conmutación automática de perfiles según el juego o aplicación activa": "Automatic profile switching based on active game or application",`
  * **Mutado:**   `"Conmutación automática de perfiles según el juego o aplicación activa": "Automatic profile switching based on active game and application",`
  * **Diagnóstico:** La suite de pruebas no detectó esta mutación. Se requiere una aserción unitaria que verifique esta bifurcación.
* **[M-02] Línea 79:** Inversión lógica (or por and)
  * **Original:** `"Duración de cada pulsación o ciclo de color": "Duration of each pulse or color cycle",`
  * **Mutado:**   `"Duración de cada pulsación o ciclo de color": "Duration of each pulse and color cycle",`
  * **Diagnóstico:** La suite de pruebas no detectó esta mutación. Se requiere una aserción unitaria que verifique esta bifurcación.
* **[M-03] Línea 113:** Inversión lógica (or por and)
  * **Original:** `"Avanzar a la siguiente pestaña en navegador o IDE (Ctrl+Tab)": "Advance to next tab in browser or IDE (Ctrl+Tab)",`
  * **Mutado:**   `"Avanzar a la siguiente pestaña en navegador o IDE (Ctrl+Tab)": "Advance to next tab in browser and IDE (Ctrl+Tab)",`
  * **Diagnóstico:** La suite de pruebas no detectó esta mutación. Se requiere una aserción unitaria que verifique esta bifurcación.
* **[M-04] Línea 121:** Inversión lógica (or por and)
  * **Original:** `"Alternar reproducción de música o video": "Toggle music or video playback",`
  * **Mutado:**   `"Alternar reproducción de música o video": "Toggle music and video playback",`
  * **Diagnóstico:** La suite de pruebas no detectó esta mutación. Se requiere una aserción unitaria que verifique esta bifurcación.

### 18. `src/services/action_catalog.py` (Score: 60.0% — 2 superviviente(s))
* **[M-01] Línea 129:** Inversión lógica (or por and)
  * **Original:** `if not isinstance(app_id, str) or not app_id.strip():`
  * **Mutado:**   `if not isinstance(app_id, str) and not app_id.strip():`
  * **Diagnóstico:** La suite de pruebas no detectó esta mutación. Se requiere una aserción unitaria que verifique esta bifurcación.
* **[M-02] Línea 144:** Inversión de desigualdad (!= por ==)
  * **Original:** `if app_name and app_name != app_id:`
  * **Mutado:**   `if app_name and app_name == app_id:`
  * **Diagnóstico:** La suite de pruebas no detectó esta mutación. Se requiere una aserción unitaria que verifique esta bifurcación.

### 19. `src/services/profile_manager.py` (Score: 40.0% — 3 superviviente(s))
* **[M-01] Línea 28:** Inversión booleana (False por True)
  * **Original:** `return getattr(self._repository, "is_corrupted", False)`
  * **Mutado:**   `return getattr(self._repository, "is_corrupted", True)`
  * **Diagnóstico:** La suite de pruebas no detectó esta mutación. Se requiere una aserción unitaria que verifique esta bifurcación.
* **[M-02] Línea 39:** Inversión booleana (True por False)
  * **Original:** `return True`
  * **Mutado:**   `return False`
  * **Diagnóstico:** La suite de pruebas no detectó esta mutación. Se requiere una aserción unitaria que verifique esta bifurcación.
* **[M-03] Línea 253:** Inversión de pertenencia (not in por in)
  * **Original:** `elif ":" not in application_id:`
  * **Mutado:**   `elif ":" in application_id:`
  * **Diagnóstico:** La suite de pruebas no detectó esta mutación. Se requiere una aserción unitaria que verifique esta bifurcación.

### 20. `src/storage/profile_repository.py` (Score: 40.0% — 3 superviviente(s))
* **[M-01] Línea 72:** Inversión booleana (False por True)
  * **Original:** `def import_data(self, data: dict, overwrite: bool = False) -> tuple[int, int]:`
  * **Mutado:**   `def import_data(self, data: dict, overwrite: bool = True) -> tuple[int, int]:`
  * **Diagnóstico:** La suite de pruebas no detectó esta mutación. Se requiere una aserción unitaria que verifique esta bifurcación.
* **[M-02] Línea 135:** Inversión booleana (True por False)
  * **Original:** `lock_path.parent.mkdir(parents=True, exist_ok=True)`
  * **Mutado:**   `lock_path.parent.mkdir(parents=False, exist_ok=True)`
  * **Diagnóstico:** La suite de pruebas no detectó esta mutación. Se requiere una aserción unitaria que verifique esta bifurcación.
* **[M-03] Línea 165:** Inversión booleana (False por True)
  * **Original:** `backup_created = False`
  * **Mutado:**   `backup_created = True`
  * **Diagnóstico:** La suite de pruebas no detectó esta mutación. Se requiere una aserción unitaria que verifique esta bifurcación.

---
_Reporte generado automáticamente por HARNESS: Sistema de Revisión en 5 Capas._
