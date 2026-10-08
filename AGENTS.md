# AGENTS.md — Logitech G502 HERO Profile Manager

Administrador avanzado de perfiles de hardware y motor de automatización reactivo para el ratón Logitech G502 HERO en Linux, construido con arquitectura limpia y GUI nativa en GTK4 / Libadwaita.

## Stack y estructura
- **Lenguaje y Entorno:** Python 3.9+ en Linux (X11 y Wayland).
- **Interfaz y Gráficos:** GTK4, Libadwaita, PyGObject y Cairo Canvas (vectorial interactivo).
- **Sistema y Hardware:** `libratbag` (`ratbagctl`), D-Bus (`Gio.DBusConnection` para StatusNotifierItem) y demonio de usuario `systemd`.
- **Estructura clave:**
  - `src/domain/`: Entidades y Value Objects puros desacoplados (Profile, Button, Action, Dpi).
  - `src/storage/`: Persistencia atómica en JSON (`JsonProfileRepository`) tolerante a fallos.
  - `src/adapters/`: Comunicación con hardware (`RatbagDeviceAdapter`) y auto-descubrimiento (Steam VDF, Epic, Desktop XDG).
  - `src/gui/`: Ventana Libadwaita, diagrama Cairo (`mouse_diagram.py`) y bandeja D-Bus (`tray.py`).
  - `src/engine.py`: Motor de monitoreo en hilo secundario para conmutación reactiva de perfiles.
  - `tests/`: Suite de 155 pruebas unitarias con mocks puros.

## Comandos
- **Ejecutar pruebas unitarias:** `python3 -m unittest discover -s tests -v`
- **Lanzar interfaz gráfica:** `python3 src/cli.py gui`
- **Iniciar motor por consola:** `python3 src/cli.py auto`
- **Verificar estado de perfiles y mouse:** `python3 src/cli.py status`
- **Revisar logs del servicio systemd:** `journalctl --user -u g502-profile-manager.service -f`

## Convenciones
- **Tipado estricto:** Usar siempre `from __future__ import annotations` y type hints.
- **Desacoplamiento:** La capa GUI o de dominio NUNCA ejecuta comandos de sistema directamente; todo pasa por adaptadores inyectables.
- **Idioma:** Código, variables y pruebas en inglés o español técnico según el módulo preexistente; comentarios y docstrings explicativos en español.

## Reglas de dominio / Trampas conocidas
1. **Mapeo de teclas y compatibilidad de juegos en `libratbag`:**
   - Teclas modificadoras (`Shift`, `Ctrl`, `Alt`, `Meta`): Usar obligatoriamente `button X action set key <KEY>`. El protocolo HID++ 2.0 rechaza modificadores en macros con `-22 (EINVAL)` y `key` permite mantener presionado (*hold*) para correr/sprint, esquivar o canalizar habilidades.
   - Teclas alfanuméricas y símbolos (`1`, `2`, `q`, `e`, `.`, etc.): Usar `button X action set macro <KEY>`. Genera la secuencia completa `↕KEY` que reconocen los motores de juego (Unreal Engine en AION 2, Wine/Proton) y neutraliza modificadores residuales pegados de `libratbag 0.18`.
   - Macros complejas (`binding_type == "macro"`): Usar `button X action set macro <MACRO_VAL>`.
   - Para símbolos y puntuación (`.`, `,`, `-`, etc.): Mapear siempre a su identificador de input-event-codes (`KEY_DOT`, `KEY_COMMA`, etc.) antes de invocar `ratbagctl`.
2. **Concurrencia e Hilos en GTK4:**
   - El bucle de eventos de GTK4 corre en el hilo principal. El motor `AutomationEngine` corre en un `threading.Thread` secundario.
   - Toda actualización a la interfaz desde el motor DEBE despacharse exclusivamente mediante `GLib.idle_add(...)`.
3. **Aislamiento de memoria física (Modelo G-HUB):**
   - Cualquier botón físico no asignado en un perfil debe restaurarse explícitamente a su valor de fábrica (`button 1..5`, `resolution-alternate`, etc.) para evitar contaminación de teclas entre juegos.
4. **Cumplimiento Anti-Cheat:**
   - Mapeo estricto de hardware 1:1. Prohibido implementar temporizadores o bucles de pulsaciones automáticas que puedan detonar sanciones de software antitrampas (EAC, BattlEye).
5. **Bandeja del sistema (Tray):**
   - Usar D-Bus nativo (`org.kde.StatusNotifierItem`). PROHIBIDO importar `AppIndicator3` (GTK3), ya que colisiona con el contexto de memoria de GTK4.

## Forma de trabajar
- **Pensar antes de programar:** Declarar suposiciones y exponer trade-offs antes de alterar código.
- **Cambios quirúrgicos:** Tocar únicamente las líneas necesarias para el objetivo solicitado. No refactorizar código adyacente que ya funciona.
- **Simplicidad:** La solución más directa y limpia posible, sin sobreingeniería especulativa.
- **Mantenimiento documental continuo:** Al completar cambios significativos o resolver bugs técnicos no evidentes, actualizar inmediatamente `MEMORY.md` (o `AGENTS.md` si cambiaron las reglas), manteniéndolo siempre conciso (máximo ~50 líneas) y sin redundancias.

## Límites
- 🟢 **Siempre:** Ejecutar la suite completa de pruebas (`155/155 OK`) antes de dar por terminada una tarea.
- ⚠️ **Pregunta antes:** Modificar el esquema de almacenamiento JSON, tocar las definiciones D-Bus del Tray o alterar el comportamiento del interruptor de auto-detección.
- 🚫 **Nunca:** Escribir directamente en `~/.config/g502-profiles.json` sin usar la capa de persistencia atómica; agregar dependencias pesadas no estándar sin autorización.

## Verificación
- Todos los cambios deben validarse ejecutando la suite de 155 pruebas:
  `python3 -m unittest discover -s tests -v` (debe concluir con código de salida 0 y 0 errores).
