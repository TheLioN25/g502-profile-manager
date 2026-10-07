# MEMORY.md — Logitech G502 Family Profile Manager

Memoria técnica del proyecto entre sesiones (~45 líneas). Estado y decisiones consolidadas.

## Estado actual
- **Soporte Multi-Variante Familia Logitech G502 (Fase 2) 100% implementado y probado.**
- **139 pruebas unitarias automatizadas** pasando al 100% (`139/139 OK`) en local y CI.
- **Variantes soportadas:** *G502 Proteus Core*, *G502 Proteus Spectrum*, *G502 HERO*, *G502 LIGHTSPEED*, *G502 X* y *G502 X PLUS / Wireless*.
- **Características operativas:**
  - Reconocimiento de variantes en 2 pasos (`ratbagctl list` + desambiguación con `info` para LEDs/DPI).
  - Adaptación contextual: límites de sensor (12.000 vs 25.600 DPI), clampeo automático en hardware, ocultamiento de RGB en G502 X y fijación de azul en Proteus Core.
  - Gestión diferida de batería (caché 30-60s) reflejada en HeaderBar de la GUI y Tooltip del Tray (`org.kde.StatusNotifierItem`).
  - Comando CLI `status` añadido (`python3 src/cli.py status`) para diagnóstico instantáneo de hardware y perfiles.

## Decisiones arquitectónicas (y por qué)
- **StatusNotifierItem directo en D-Bus (`Gio.DBusConnection`):** En lugar de usar `AppIndicator3` (GTK3 que crashea en GTK4), se implementó D-Bus nativo con porcentaje de batería sin modificar XML.
- **Sintaxis híbrida `key` vs `macro` en `ratbag_adapter`:**
  - Teclas modificadoras (`Shift`, `Ctrl`, `Alt`, `Meta`): `action set key <KEY>` obligatorio por HID++ 2.0 (-22 EINVAL en macros) y soporte continuo (hold).
  - Teclas estándar alfanuméricas y símbolos: `action set macro <KEY>` (`↕KEY`) para Proton/Wine/UE5 en AION 2 y neutralización de modificadores pegados en libratbag 0.18.
- **Aceleración Adaptativa (`Adaptive`) en KDE/Wayland:** `PointerAccelerationProfile=1` en `kcminputrc` y D-Bus para evitar resistencia artificial a altos DPIs.
- **Persistencia atómica y DDD:** Perfiles universales agnósticos al modelo físico sin tocar esquema JSON existente.
- **Aislamiento total y anti-drift:** Restauración de botones a fábrica en hardware y re-sincronización ante derive físico (G9).

## Próximos pasos y Hoja de Ruta Prioritaria
- Paquete AUR publicado en cuanto se reactiven registros en aur.archlinux.org (PKGBUILD ya probado).
