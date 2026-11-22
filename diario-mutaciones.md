# 📔 Diario de Pruebas Mutantes — g502-profile-manager

**Fecha del escaneo:** 2026-11-16 23:35:42  
**Ruta del proyecto:** `/home/thelion/SSD/Proyectos/g502-profile-manager`  
**Total módulos analizados:** 28  
**Módulos 100% blindados:** 28 / 28  
**Módulos con deuda de mutación:** 0 (Completado)  
**Score global de mutación:** 100.0% (107/107 mutantes eliminados)

---

## 🟢 Módulos Blindados Inicialmente (100% Mutantes Eliminados)
- [x] `src/adapters/__init__.py` (Sin operadores de mutación aplicables)
- [x] `src/adapters/action_presets.py` (Sin operadores de mutación aplicables)
- [x] `src/adapters/application_resolver.py` (5/5 eliminados)
- [x] `src/domain/__init__.py` (Sin operadores de mutación aplicables)
- [x] `src/engine.py` (5/5 eliminados)
- [x] `src/gui/__init__.py` (Sin operadores de mutación aplicables)
- [x] `src/services/__init__.py` (Sin operadores de mutación aplicables)
- [x] `src/storage/__init__.py` (Sin operadores de mutación aplicables)

---

## 🟢 Módulos Blindados en esta Campaña (100% Mutantes Eliminados — 20/20)
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

### ~~9. `src/domain/application.py`~~ ✅ BLINDADO (Score: 60.0% → 100% — 3/3 eliminados)
> Resuelto — Tests: `test_action_is_immutable` (aniquilación de M-01 validando inmutabilidad con `FrozenInstanceError`) y `test_action_binding_type_and_category_fallbacks` (aniquilación de M-02 validando conjunción `and` ante valores vacíos o no-string).

### ~~10. `src/domain/device.py`~~ ✅ BLINDADO (Score: 20.0% → 100% — 3/3 eliminados)
> Resuelto — Tests: `test_device_capabilities_defaults_and_immutability` (aniquilación de M-01 validando `FrozenInstanceError`, M-02 comprobando `has_lighting=True`, M-03 comprobando `has_rgb=True` y M-04 comprobando `has_battery=False`) y `test_button_immutability` (inmutabilidad estricta de Button).

### ~~11. `src/domain/profile.py`~~ ✅ BLINDADO (Score: 80.0% → 100% — 3/3 eliminados)
> Resuelto — Tests: `test_dpi_configuration_is_immutable` (aniquilación de M-01 validando `FrozenInstanceError` al mutar `dpi` o `shift_dpi`), y suite dedicada `TestDomainAssignment` verificando creación, tipado estricto e inmutabilidad (`FrozenInstanceError`) para `Assignment`.

### ~~12. `src/gui/app.py`~~ ✅ BLINDADO (Score: 50.0% → 100% — 2/2 eliminados)
> Resuelto — Test `test_app_do_activate_instantiates_window_with_start_auto` en `tests/test_gui_window_logic.py` (aniquilación de M-01 comprobando que `MainWindow` se inicialice obligatoriamente con `start_auto=True` e idempotencia del ciclo de activación).

### ~~13. `src/gui/dialogs.py`~~ ✅ BLINDADO (Score: 0.0% → 100% — 3/3 eliminados)
> Resuelto — Test `test_action_picker_dialog` en `tests/test_gui_window_logic.py` (aniquilación de M-01 validando `get_modal()`, M-02 comprobando `get_hexpand()` en buscador, M-03 y M-04 comprobando `get_vexpand()` y `get_hexpand()` en ScrolledWindow contenedor vía Viewport, M-05 comprobando `get_activatable()` y activación funcional por señal `activated`, más blindaje de modalidad preventivo en `NewProfileDialog`).

### ~~14. `src/gui/mouse_diagram.py`~~ ✅ BLINDADO (Score: 40.0% → 100% — 3/3 eliminados)
> Resuelto — Tests `test_diagram_initial_properties` (aniquilación de M-01 validando `get_hexpand()=False` y M-02 comprobando `get_vexpand()=True`) y `test_set_led_color` (aniquilación de M-03 validando parseo RGB con códigos hex válidos de 6 dígitos e invariancia ante longitudes inválidas).

### ~~15. `src/gui/tray.py`~~ ✅ BLINDADO (Score: 80.0% → 100% — 3/3 eliminados)
> Resuelto — Test `test_sni_introspection_xml_validity` en `tests/test_gui_tray.py` (aniquilación de M-01 validando el parseo XML sin errores y la existencia de la propiedad `Category` de tipo `s` en la interfaz `org.kde.StatusNotifierItem`).

### ~~16. `src/gui/window.py`~~ ✅ BLINDADO (Score: 80.0% → 100% — 3/3 eliminados)
> Resuelto — Test `test_main_window_default_notifications_enabled_when_manager_lacks_method` en `tests/test_gui_window_logic.py` (aniquilación de M-01 comprobando que `initial_notif` sea `True` por defecto cuando el gestor carece del método `get_notifications_enabled`).

### ~~17. `src/i18n.py`~~ ✅ BLINDADO (Score: 20.0% → 100% — 3/3 eliminados)
> Resuelto — Test `test_translation_to_english` en `tests/test_i18n.py` (aniquilación de M-01, M-02, M-03 y M-04 comprobando las traducciones exactas de cadenas que contienen conjunciones lógicas 'or' al inglés sin degradación a español ni distorsión por 'and').

### ~~18. `src/services/action_catalog.py`~~ ✅ BLINDADO (Score: 60.0% → 100% — 3/3 eliminados)
> Resuelto — Tests `test_parse_and_register_manifest_invalid_application_id_safely_ignored` (aniquilación de M-01 comprobando el rechazo seguro ante IDs no-string o vacíos mediante conjunción 'or') y `test_parse_and_register_manifest_updates_name_when_distinct_from_id` (aniquilación de M-02 comprobando la actualización a nombres legibles cuando `name != id`).

### ~~19. `src/services/profile_manager.py`~~ ✅ BLINDADO (Score: 40.0% → 100% — 3/3 eliminados)
> Resuelto — Tests `test_profile_manager_defaults_when_repository_lacks_features` (aniquilación de M-01 validando `is_corrupted=False` y M-02 comprobando `get_notifications_enabled=True` ante repositorios con capacidades limitadas) y `test_get_target_profile_for_app_desktop_fallback_without_colon` (aniquilación de M-03 comprobando la resolución reactiva de apps de escritorio con prefijo implícito `desktop:`).

### ~~20. `src/storage/profile_repository.py`~~ ✅ BLINDADO (Score: 40.0% → 100% — 3/3 eliminados)
> Resuelto — Tests `test_profile_repository_import_data_signature_defaults_to_overwrite_false` (aniquilación de M-01 comprobando por introspección que `overwrite=False` sea el valor por defecto en `ProfileRepository`), `test_file_lock_creates_nested_parent_directories` (aniquilación de M-02 comprobando creación recursiva de directorios padres en `_file_lock`) y `test_handle_corrupted_file_when_copy_fails_sets_backup_created_false` (aniquilación de M-03 comprobando manejo resiliente si la copia de respaldo falla por I/O).

---
_Reporte generado automáticamente por HARNESS: Sistema de Revisión en 5 Capas._
