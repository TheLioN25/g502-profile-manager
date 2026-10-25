# MEMORY.md — Logitech G502 Family Profile Manager

Memoria técnica del proyecto entre sesiones (~45 líneas). Estado y decisiones consolidadas.

## Estado actual
- **Versión 0.5.0: Auditoría cruzada aprobada, Wheel funcional, Persistencia tolerante a fallos y 173 Tests.**
- **Robustez de persistencia y concurrencia (R-02, R-04):**
  - Respaldo automático `.corrupt-<timestamp>` y bloqueo de sobreescrituras ante archivos corruptos (`CorruptedProfileRepositoryError`).
  - Sincronización dual: `threading.RLock` (hilos internos) y `fcntl.flock` sobre `.lock` (procesos GUI/CLI concurrentes).
  - Escrituras atómicas con `tempfile.NamedTemporaryFile` previniendo colisiones de PID.
- **Empaquetado distribuible y CI (R-01, R-11):**
  - Wheel funcional con `py-modules` (`cli`, `engine`, `i18n`) y recursos empaquetados (`presets/`, `icons/`).
  - Smoke test en entorno limpio integrado en GitHub Actions validando imports y entry points (`g502 --help`).
  - Unificación estricta de versión mínima en `Python >=3.10`.
- **Hardware y Adaptadores (R-05, R-09, R-10):**
  - Eliminación de `except TypeError` ciego en motor y de heurística de mocks en `RatbagDeviceAdapter`.
  - Validación de teclas y rechazo de símbolos no soportados con `ValueError` en CLI y adaptador.
  - Servicio systemd generado dinámicamente apuntando al launcher instalado (`g502 run`) sin rutas de desarrollo.
- **173 pruebas unitarias automatizadas** pasando al 100% (`173/173 OK`) en local.
- **Variantes soportadas:** *G502 Proteus Core*, *G502 Proteus Spectrum*, *G502 HERO*, *G502 LIGHTSPEED*, *G502 X* y *G502 X PLUS / Wireless*.
- **Características operativas:**
  - Reconocimiento de variantes en 2 pasos (`ratbagctl list` + desambiguación con `info` para LEDs/DPI).
  - Escrituras diferenciales (`diff_only=True`) con persistencia compartida en disco (`~/.config/g502-hardware-state.json`).
  - Internacionalización bilingüe completa (ES/EN) con selector en HeaderBar, tray D-Bus y catálogo.
  - Set de iconos multi-resolución en `data/icons/` y `src/gui/icons/` con diseño *squircle* y silueta 3D.

## Decisiones arquitectónicas (y por qué)
- **Persistencia atómica y resiliente:** Ruta canónica resuelta dinámicamente mediante `get_default_profiles_file()` (`~/.config/g502-profiles.json`). Respaldo inmediato ante corrupción previa para evitar pérdida de datos del usuario.
- **Doble candado de concurrencia:** `RLock` de memoria para motor/hilos y `flock` de archivo para comandos CLI concurrentes.
- **StatusNotifierItem directo en D-Bus (`Gio.DBusConnection`):** D-Bus nativo sin `AppIndicator3` (GTK3 que crashea en GTK4).
- **Sincronización remota pre-auditoría:** Push a origin/master con 173 tests en verde para validar GitHub Actions CI; la re-revisión de OpenCode auditará este delta publicado y cualquier ajuste se aplicará en commit incremental.
- **Sintaxis híbrida `key` vs `macro` en `ratbag_adapter`:**
  - Modificadores (`Shift`, `Ctrl`, `Alt`, `Meta`): `action set key <KEY>` por HID++ 2.0 (-22 EINVAL en macros) y soporte hold.
  - Alfanuméricas y símbolos: `action set macro <KEY>` (`↕KEY`) para Wine/Proton/UE5. Rechazo estricto con `ValueError` para símbolos no soportados.

## Próximos pasos y Hoja de Ruta Prioritaria
- Re-revisión de cierre por OpenCode sobre el delta congelado (`56543e4` → `8a66fb5`).
- Hito dedicado de deuda técnica (R-12): modularizar `MainWindow` introduciendo `typing.Protocol` para adaptadores.
- Publicación formal de la versión 0.5.0 y paquete AUR cuando se reactiven registros en aur.archlinux.org.
