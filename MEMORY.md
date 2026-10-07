# MEMORY.md — Logitech G502 Family Profile Manager

Memoria técnica del proyecto entre sesiones (~45 líneas). Estado y decisiones consolidadas.

## Estado actual
- **Soporte Multi-Variante Familia Logitech G502 (Fase 2) e Internacionalización Bilingüe (Fases 3, 3.1 y 3.2) 100% completados.**
- **154 pruebas unitarias automatizadas** pasando al 100% (`154/154 OK`) en local y GitHub Actions CI.
- **Variantes soportadas:** *G502 Proteus Core*, *G502 Proteus Spectrum*, *G502 HERO*, *G502 LIGHTSPEED*, *G502 X* y *G502 X PLUS / Wireless*.
- **Características operativas:**
  - Reconocimiento de variantes en 2 pasos (`ratbagctl list` + desambiguación con `info` para LEDs/DPI).
  - Adaptación contextual: límites de sensor (12.000 vs 25.600 DPI), clampeo automático en hardware, ocultamiento de RGB en G502 X y fijación de azul en Proteus Core.
  - Gestión diferida de batería (caché 30-60s) reflejada en HeaderBar de la GUI y Tooltip del Tray (`org.kde.StatusNotifierItem`).
  - Comando CLI `status` añadido (`python3 src/cli.py status`) para diagnóstico instantáneo de hardware y perfiles.
  - Internacionalización bilingüe completa (ES/EN): `src/i18n.py`, selector en HeaderBar, tray D-Bus, catálogo, diagrama Cairo, iluminación LED (paleta, velocidades, descripciones), diálogos modales (feedback comunitario, nuevo perfil, asignación) y persistencia atómica en `~/.config/g502-preferences.json`.
  - Script de detección regional de idioma (`scripts/detect-locale.sh`) integrado en primera ejecución e instalador (`scripts/install-bin.sh`).
  - Documentación bilingüe oficial en GitHub (Fase 3.1): `README.md` (inglés primario), `README.es.md` (español) y selector de navegación lingüística recíproco.

## Decisiones arquitectónicas (y por qué)
- **Detección regional automática (Fase 3.2):** Si no existe configuración previa, `I18nManager` analiza `$LC_ALL`, `$LC_MESSAGES`, `$LANG` para auto-seleccionar `es` o `en` (resto del mundo).
- **StatusNotifierItem directo en D-Bus (`Gio.DBusConnection`):** D-Bus nativo sin `AppIndicator3` (GTK3 que crashea en GTK4).
- **Sintaxis híbrida `key` vs `macro` en `ratbag_adapter`:**
  - Modificadores (`Shift`, `Ctrl`, `Alt`, `Meta`): `action set key <KEY>` por HID++ 2.0 (-22 EINVAL en macros) y soporte hold.
  - Alfanuméricas y símbolos: `action set macro <KEY>` (`↕KEY`) para Wine/Proton/UE5 y neutralización de modificadores pegados en libratbag 0.18.
- **Aceleración Adaptativa (`Adaptive`) en KDE/Wayland:** `PointerAccelerationProfile=1` en `kcminputrc` y D-Bus.
- **Persistencia atómica y DDD:** Perfiles universales agnósticos al modelo físico sin tocar esquema JSON existente.

## Próximos pasos y Hoja de Ruta Prioritaria
- Paquete AUR publicado en cuanto se reactiven registros en aur.archlinux.org (PKGBUILD ya probado).
