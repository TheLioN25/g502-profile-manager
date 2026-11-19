# MEMORY.md — Logitech G502 Family Profile Manager

Memoria técnica del proyecto entre sesiones (~45 líneas). Estado y decisiones consolidadas.

## Estado actual
- **Versión 0.6.0: Soporte Wine/Proton, shortcuts.vdf binario de Steam, preset Soulframe y resolución de procesos dinámicos con anti-flapping. Suite al 100% (`OK`, 244 tests).**
- **Robustez de persistencia y concurrencia (R-02, R-04, C-08):**
  - Respaldo automático `.corrupt-<timestamp>` y bloqueo de sobreescrituras ante archivos corruptos (`CorruptedProfileRepositoryError`).
  - Sincronización dual: `threading.RLock` (hilos internos) y `fcntl.flock` sobre `.lock` (procesos GUI/CLI concurrentes).
  - Rollback de preferencias de notificación en memoria si `_flush()` falla por E/S; reversión de toggle y toast en GUI.
- **Hardware, Anti-Bucle y Protección de EEPROM (C-01, C-02, C-07):**
  - Backoff exponencial (`_register_apply_failure` 2s→4s→8s…60s) ante fallos de hardware aislando objetivos (`target_key`).
  - `restore_desktop` verifica confirmación del hardware antes de notificar y no limpia estado si falla.
  - Detección conservadora de zonas LED (`_probe_led_count`) en familia G502 X: no escribe zonas inexistentes y no cachea si `info` no responde.
- **Notificaciones OSD y D-Bus Resiliente (C-03, C-04, C-05, C-06, R-23):**
  - Reintento de sesión Gio D-Bus tras enfriamiento real de 30s (`_dbus_retry_cooldown_sec`).
  - Fallback `notify-send` acotado a 1.0s con hint booleano canónico (`boolean:transient:true`).
  - Contrato formal verificado para llamada D-Bus `Notify` y Kill-Switch persistente en HeaderBar.
- **Suite de pruebas unitarias automatizadas** pasando al 100% (`OK`, 244 tests) en local y mutantes eliminados al 100% en Capa 2 (Harness).
- **Resolución reactiva de perfiles:** Prioriza perfiles con asignaciones sobre vacíos en resolución canónica (`_resolve_target_profile_for_app`), previene secuestros por subcadenas difusas y ordena videojuegos antes que utilidades de fondo (`ActiveApplication.is_game`).
- **Soporte Non-Steam Games y Juegos Wine/Proton (Hitos 1, 2 y 3):**
  - Decodificación pura de `shortcuts.vdf` binario Valve en `steam_discovery.py` sanitizando comillas en rutas.
  - Resolución dinámica de procesos y binarios secundarios (`Soulframe.x64.exe`) mediante `alias_map` y heurística de subárbol en `application_resolver.py`.
  - Protección anti-flapping en `engine.py` con ventana de gracia configurable (3s) en la transición launcher -> binario real.
- **Variantes soportadas:** *G502 Proteus Core*, *G502 Proteus Spectrum*, *G502 HERO*, *G502 LIGHTSPEED*, *G502 X* y *G502 X PLUS / Wireless*.

## Decisiones arquitectónicas (y por qué)
- **Persistencia atómica y resiliente:** Ruta canónica resuelta dinámicamente mediante `get_default_profiles_file()` (`~/.config/g502-profiles.json`). Cero cambios de esquema JSON.
- **Doble candado de concurrencia:** `RLock` de memoria para motor/hilos y `flock` de archivo para comandos CLI concurrentes.
- **StatusNotifierItem directo en D-Bus (`Gio.DBusConnection`):** D-Bus nativo sin `AppIndicator3` (GTK3 que crashea en GTK4).
- **Protección contra desgaste flash:** Ante error de controlador, el backoff corta reescrituras continuas a 1 intento/min.
- **Sintaxis híbrida `key` vs `macro` en `ratbag_adapter`:**
  - Modificadores (`Shift`, `Ctrl`, `Alt`, `Meta`): `action set key <KEY>` por HID++ 2.0 (-22 EINVAL en macros) y soporte hold.
  - Alfanuméricas y símbolos: `action set macro <KEY>` (`↕KEY`) para Wine/Proton/UE5. Rechazo estricto con `ValueError` para símbolos no soportados.

## Próximos pasos y Hoja de Ruta Prioritaria
- Re-revisión y validación de cierre por OpenCode con `response.md` (C-01…C-08 sobre R-14…R-22).
- Petición de datos reales de `g502 status` a dueños de G502 X LIGHTSPEED en notas de release.
- Hito dedicado de deuda técnica (R-12): modularizar `MainWindow` introduciendo `typing.Protocol` para adaptadores.
