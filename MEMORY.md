# MEMORY.md — Logitech G502 HERO Profile Manager

Memoria técnica del proyecto entre sesiones (~45 líneas). Estado y decisiones consolidadas.

## Estado actual
- **Versión v1.0.0 pública y 100% funcional** en GitHub (`TheLioN25/g502-profile-manager`).
- **128 pruebas unitarias automatizadas** pasando al 100% en local y en el pipeline CI de GitHub Actions.
- **Características operativas:**
  - GUI completa en GTK4/Libadwaita con plano vectorial interactivo (Cairo) y selector de perfiles por aplicación.
  - Auto-detección reactiva integrada en HeaderBar (`engine.py` en hilo secundario con Steam VDF, Epic y Desktop).
  - Bandeja del sistema (`tray.py`) mediante StatusNotifierItem D-Bus nativo para KDE Plasma y GNOME.
  - Catálogo modular de acciones extensible con soporte dinámico de alias y coincidencia difusa (MMORPGs, Shooters, etc.).
  - Aislamiento total de perfiles en hardware y servicio `systemd --user` configurable.

## Decisiones arquitectónicas (y por qué)
- **StatusNotifierItem directo en D-Bus (`Gio.DBusConnection`):** En lugar de usar `AppIndicator3` (GTK3 que crashea en GTK4), se implementó D-Bus nativo, logrando cero dependencias externas conflictivas.
- **Sintaxis híbrida `key` vs `macro` en `ratbag_adapter`:**
  - Teclas modificadoras (`Shift`, `Ctrl`, `Alt`, `Meta`): Usar obligatoriamente `action set key <KEY>`. El protocolo HID++ 2.0 rechaza modificadores en macros con `-22 (EINVAL)` y `key` permite mantener presionado (*hold*) para correr/acelerar.
  - Teclas estándar alfanuméricas (`1`, `2`, `e`, `r`): Usar `action set macro <KEY>` para forzar `modifiers=0` y neutralizar modificadores residuales pegados de `libratbag 0.18`.
  - Puntuación y navegación (`.`, `,`, `-`, `=`, `/`, `[`, `]`, `space`, etc.): Mapeo integral a `KEY_DOT`, `KEY_COMMA`, etc., evitando errores de `ratbagctl`.
- **Aceleración Plana (`Flat`) en KDE/Wayland:** Se persiste `pointerAccelerationProfile=1` en `kcminputrc` para garantizar lectura 1:1 pura del sensor HERO sin frenado ni resistencia no lineal.
- **Persistencia atómica temporal (`.tmp` + rename atómico):** Evita archivos JSON corruptos ante caídas o reinicios.
- **Diseño Domain-Driven (DDD):** El dominio de botones, DPI y acciones es agnóstico a GTK y a ratbagctl, permitiendo testear el 100% de la lógica con mocks puros en milisegundos.

## Próximos pasos y Hoja de Ruta Prioritaria
- **🎯 OBJETIVO PRINCIPAL PRÓXIMA SESIÓN:** Ampliar compatibilidad a toda la familia Logitech G502:
  - Variantes a soportar: *G502 Proteus Core*, *G502 Proteus Spectrum*, *G502 LIGHTSPEED* (inalámbrico/USB receiver) y *G502 X / X PLUS*.
  - Lectura dinámica de IDs y perfiles de hardware desde `libratbag` (`ratbagctl list`).
  - Detección automática del modelo conectado para que la interfaz adapte el título y los comandos sin perder la asignación 1:1.
- Paquete AUR publicado en cuanto se reactiven registros en aur.archlinux.org (PKGBUILD ya probado).
