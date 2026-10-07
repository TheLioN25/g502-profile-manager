# Especificación Técnica: Soporte Multi-Variante Familia Logitech G502

## 1. Resumen y Objetivos
Expandir la compatibilidad de *G502 Profile Manager* para reconocer y gestionar nativamente cualquiera de las 6 variantes comerciales de la familia Logitech G502 en Linux mediante `libratbag`, adaptando dinámicamente las capacidades de la interfaz (DPI máximos, iluminación y batería) sin alterar la arquitectura limpia ni romper los 128 tests existentes.

---

## 2. Matriz de Variantes de Hardware

| Variante Comercial | Identificador Canónico | USB VID:PID | Sensor Máx | Iluminación | Batería |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **G502 Proteus Core** | `g502_proteus_core` | `046d:c07d` | 12.000 DPI | 1 zona (Monocromo azul) | No |
| **G502 Proteus Spectrum** | `g502_proteus_spectrum` | `046d:c332` | 12.000 DPI | 2 zonas RGB | No |
| **G502 HERO** *(Actual)* | `g502_hero` | `046d:c08b` | 25.600 DPI | 2 zonas RGB | No |
| **G502 LIGHTSPEED** | `g502_lightspeed` | `046d:407f` / `046d:c08d` | 25.600 DPI | 2 zonas RGB | Sí (Inalámbrico) |
| **G502 X** | `g502_x` | `046d:c099` | 25.600 DPI | Sin RGB (Solo indicador DPI) | No |
| **G502 X Wireless / PLUS** | `g502_x_wireless` | `046d:c098` | 25.600 DPI | 8 zonas Lightform RGB | Sí (Inalámbrico) |

> **Matriz Común:** Todas las variantes usan `Driver=hidpp20` en `libratbag` y comparten la misma disposición física de 11 botones: LEFT (0), RIGHT (1), MIDDLE (2), G4 (3), G5 (4), SNIPER (5), G7 (6), G8 (7), G9 (8), WHEEL_RIGHT (9), WHEEL_LEFT (10).

---

## 3. Arquitectura y Componentes

### A. Capa de Dominio (`src/domain/device.py`)
- Entidades inmutables `DeviceCapabilities` y `DeviceVariant`.
- Catálogo de fábrica inmutable con las 6 variantes.
- Fallback automático a `G502 HERO` si el dispositivo no está catalogado.

### B. Capa de Adaptador de Hardware (`src/adapters/ratbag_adapter.py`)
- Búsqueda por patrón regex `r"Logitech.*G502.*"` y `r"Logitech.*Lightspeed.*"`.
- Método `detect_device_variant(device_id: str) -> DeviceVariant`.
- Método `get_battery_level(device_id: str) -> int | None`.

### C. Motor de Automatización (`src/engine.py`)
- Uso del resolvedor dinámico para enlazar con cualquier variante detectada (cable o inalámbrico).

### D. Interfaz Gráfica (GTK4 / Libadwaita — `src/gui/`)
- Etiqueta de cabecera con modelo comercial y batería si aplica (`🔋 85%`).
- Adaptación contextual de controles de iluminación (ocultar en G502 X, fijar en Proteus Core).
- Límite superior de slider DPI adaptado (12.000 vs 25.600).
- Tooltip de `tray.py` actualizado con porcentaje de batería.

---

## 4. Criterios de Aceptación
1. Fixtures y pruebas simuladas para las 6 variantes.
2. Los 128 tests existentes se mantienen en 100% pasando (`128/128 OK`).
3. Nuevas pruebas unitarias dedicadas para dominio y adaptador de dispositivos.
