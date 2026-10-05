# MEMORY.md — Logitech G502 HERO Profile Manager

Memoria técnica del proyecto entre sesiones (~40 líneas). Estado y decisiones consolidadas.

## Estado actual
- **Versión v1.0.0 pública y 100% funcional** en GitHub (`TheLioN25/g502-profile-manager`).
- **126 pruebas unitarias automatizadas** pasando al 100% en local y en el pipeline CI de GitHub Actions.
- **Características operativas:**
  - GUI completa en GTK4/Libadwaita con plano vectorial interactivo (Cairo) y selector de perfiles por aplicación.
  - Auto-detección reactiva integrada en HeaderBar (`engine.py` en hilo secundario con Steam VDF, Epic y Desktop).
  - Bandeja del sistema (`tray.py`) mediante StatusNotifierItem D-Bus nativo para KDE Plasma y GNOME.
  - Aislamiento total de perfiles en hardware y servicio `systemd --user` configurable.

## Decisiones arquitectónicas (y por qué)
- **StatusNotifierItem directo en D-Bus (`Gio.DBusConnection`):** En lugar de usar `AppIndicator3` (librería obsoleta de GTK3 que crashea en GTK4), se implementó el protocolo D-Bus puro, logrando cero dependencias externas conflictivas.
- **Uso exclusivo de sintaxis `macro` en `ratbag_adapter`:** Resuelve el bug upstream de `libratbag 0.18` que deja modificadores residuales (`Ctrl`/`Alt`) en la EEPROM física del ratón al usar `action set key`.
- **Persistencia atómica temporal (`.tmp` + rename atómico):** Evita archivos JSON corruptos si el usuario apaga el PC o mata el proceso mientras se guarda un perfil.
- **Diseño Domain-Driven (DDD):** El dominio de botones, DPI y acciones es agnóstico a GTK y a ratbagctl, permitiendo testear el 100% de la lógica con mocks puros en milisegundos.

## Aprendizajes y errores a evitar
- NUNCA usar `action set key` con `ratbagctl` en botones laterales o con historial de macros: siempre usar `action set macro <TECLA>`.
- NUNCA llamar a métodos de widgets GTK desde hilos de trabajo: usar obligatoriamente `GLib.idle_add`.

## Próximos pasos y Hoja de Ruta Prioritaria
- **🎯 OBJETIVO PRINCIPAL PRÓXIMA SESIÓN:** Ampliar compatibilidad a toda la familia Logitech G502:
  - Variantes a soportar: *G502 Proteus Core*, *G502 Proteus Spectrum*, *G502 LIGHTSPEED* (inalámbrico/USB receiver) y *G502 X / X PLUS*.
  - Lectura dinámica de IDs y perfiles de hardware desde `libratbag` (`ratbagctl list`).
  - Detección automática del modelo conectado para que la interfaz adapte el título y los comandos sin perder la asignación 1:1.
- Paquete AUR publicado en cuanto se reactiven registros en aur.archlinux.org (PKGBUILD ya probado).
- Explorar detección fina de foco por ventanas nativas en Wayland si se requiere alternar perfiles por ventana.
