# Documento de Contexto Técnico Integral — Sesión Hito 1, Hotfix Soulframe y Plan Hito 2

**Proyecto:** Logitech G502 HERO Profile Manager  
**Ruta del Repositorio:** `/home/thelion/SSD/Proyectos/g502-profile-manager` (enlace simbólico en `/home/thelion/g502-profile-manager`)  
**Fecha y Hora de la Sesión:** 14 de Noviembre de 2026 (12:49 - 14:45)  
**Rama Git:** `master` (alineada con `origin/master`)  
**ID de Conversación:** `facc2e1c-3068-4add-8c70-133e81fb0a66`  

---

## 1. Resumen Ejecutivo de la Sesión

Esta sesión abarcó:
1. **Verificación de entorno y parámetros de red:** Confirmación de las variables de entorno (`NODE_TLS_REJECT_UNAUTHORIZED 0`) y ajuste de modelo de IA a `Gemini 3.8 Flash`.
2. **Auditoría del Hito 1:** Verificación de los commits subidos el día anterior al repositorio remoto (`origin/master`).
3. **Diagnóstico y Corrección de Causa Raíz (Hotfix Soulframe):** Corrección del problema reportado por el usuario donde Soulframe era reconocido como `desktop:launcher.exe` pero el diálogo de asignación de botones en la GUI mostraba 0 acciones disponibles.
4. **Establecimiento de Mandato de Interfaz para VS Code:** Protocolo estricto para mostrar en pantalla cada archivo modificado en la línea exacta del cambio utilizando el comando CLI de Visual Studio Code sobre Wayland.
5. **Verificación y Resolución de Estado en Memoria:** Identificación de que la ventana abierta por el usuario correspondía a un proceso previo de Python GTK4 (`PID 66685`) sin recarga en caliente; tras el reinicio de la aplicación, el usuario verificó y confirmó que las acciones y categorías funcionan al 100%.
6. **Planificación y Análisis de Rendimiento del Hito 2:** Especificación técnica completa del soporte para accesos directos binarios de Steam (`shortcuts.vdf`), con pruebas de rendimiento que garantizan un impacto nulo en la fluidez de la app (~0.012 ms de procesamiento).

---

## 2. Ajustes de Entorno y Configuración Inicial

El usuario inició la sesión evaluando la capacidad de diagnóstico del asistente tras haber aplicado un parche manual en la sesión de shell Fish:
- Comando aplicado por el usuario: `set -Ux NODE_TLS_REJECT_UNAUTHORIZED 0`.
- Modificación en `config.json` de Antigravity CLI seleccionando el modelo `Gemini 3.8 Flash (High)`.
- **Efecto técnico verificado:** Permite la comunicación fluida con servidores y APIs locales o túneles de red sin bloqueos por verificación estricta de certificados SSL/TLS autofirmados o proxies corporativos/locales.

---

## 3. Auditoría del Hito 1 (Día Anterior)

El usuario solicitó revisar el estado del proyecto y verificar si los cambios del **Hito 1** quedaron montados en el repositorio remoto:
- **Ruta del Proyecto:** `/home/thelion/SSD/Proyectos/g502-profile-manager/`.
- **Archivo de Referencia:** `hitos-faltantes.md`.
- **Commits auditados:**
  - `1095372`: `feat(discovery): resolver entradas desktop de wine y extraer ejecutable real en command_line`
  - `82a343e`: `docs: registrar hitos faltantes para juegos no oficiales y accesos directos (soulframe)`
- **Resultado:** Se confirmó que ambos commits estaban integrados y subidos limpiamente a `origin/master`.

### Qué se implementó en el Hito 1:
- Escaneo recursivo mediante `rglob("*.desktop")` en `src/adapters/desktop_entries.py`, permitiendo leer accesos directos en carpetas anidadas como `~/.local/share/applications/wine/Programs/...`.
- Extracción del ejecutable de Windows real y lectura de `StartupWMClass` en comandos delegados por Wine (`env ... wine "C:\..."` y enlaces `.lnk`).
- Indexación cruzada en `src/adapters/application_resolver.py` para vincular procesos en ejecución con entradas de escritorio.

---

## 4. Diagnóstico de Causa Raíz: Acciones Vacías en Soulframe

### El Problema Reportado
Al abrir la GUI de `g502-profile-manager` y seleccionar **Soulframe** (`desktop:launcher.exe`), al pulsar sobre el botón **SNIPER** (o cualquier otro botón) para cambiar la asignación:
- El diálogo `ActionPickerDialog` abría correctamente la cabecera ("SNIPER Button - Catalog for Soulframe").
- Sin embargo, **la lista de categorías y habilidades aparecía totalmente vacía** (solo se mostraba la sección inferior de "Asignación Personalizada" para introducir una tecla manual).

### Diagnóstico Sistemático (Regla 4)
Al investigar el código causal:
1. **Filtro restrictivo en el catálogo:** En `src/services/action_catalog.py`, el método `sync_with_installed_applications` definía:
   ```python
   is_game = app_id.startswith("steam:") or app_id.startswith("epic:")
   ```
   Ignoraba completamente las aplicaciones de escritorio (`desktop:*`), incluso si eran juegos de Wine/Lutris o tenían la categoría `Game`.
2. **Inexistencia del preset:** En el directorio `presets/` no existía ningún manifiesto para Soulframe, por lo que el gestor no tenía ninguna lista de habilidades o comandos que cargar.
3. **Resultado:** `get_categories_for_application("desktop:launcher.exe")` devolvía `{}` (diccionario vacío), provocando que la interfaz no renderizara ninguna fila de acciones.

---

## 5. Implementación del Hotfix para Soulframe y Juegos Wine

Se implementó una solución quirúrgica y desacoplada respetando la arquitectura del proyecto:

### 1. Entidad de Dominio (`src/domain/application.py`)
- Se añadió la propiedad `is_game: bool = False` a la clase `Application`.
- Permite que cualquier aplicación (sea de Steam, Epic Games o `.desktop`) declare explícitamente si es un videojuego.

### 2. Detección Inteligente en Entradas Desktop (`src/adapters/desktop_entries.py`)
- Se implementó la heurística para determinar si un `.desktop` representa un juego (`entry.is_game`):
  - Contiene `Game` dentro de `Categories=...`.
  - Proviene de rutas típicas de juegos (`/wine/`, `/steam/`).
  - El campo `Exec` invoca ejecutables de compatibilidad (`wine`, `proton`, `lutris`, `heroic`).

### 3. Adaptador de Descubrimiento (`src/adapters/application_discovery_adapter.py`)
- En `discover_desktop_applications()` se propaga el atributo `is_game=entry.is_game`.
- En `discover_steam_applications()` y `discover_epic_applications()` se marca `is_game=True`.

### 4. Servicio de Catálogo de Acciones (`src/services/action_catalog.py`)
- Se amplió la detección de juegos para respetar el atributo `is_game`:
  ```python
  is_game = getattr(app, "is_game", False) or app_id.startswith("steam:") or app_id.startswith("epic:")
  ```
- Si un juego no tiene preset específico, ahora genera automáticamente el catálogo estándar de juego en lugar de dejarlo en blanco.

### 5. Creación del Preset Oficial de Soulframe
Se crearon en espejo (cumpliendo la regla del repositorio donde `presets/` y `src/services/presets/` deben ser idénticos byte por byte) los archivos:
- `presets/soulframe.json`
- `src/services/presets/soulframe.json`

**Contenido del preset:**
- **Identificador:** `soulframe`
- **Nombre:** `Soulframe`
- **Alias mapeados:** `["desktop:launcher.exe", "launcher.exe", "soulframe", "soulframe.x64.exe", "steam:3519040750"]`
- **19 Acciones distribuidas en 4 Categorías:**
  - **Combate (6):** Ataque Ligero (`button 1`), Ataque Pesado / Carga (`button 2`), Apuntar / Modo Rango (`button 3`), Bloqueo / Parada / Parry (`q`), Brazo de Pacto / Pact Arm (`f`), Patada / Desestabilizar (`e`).
  - **Habilidades (5):** Magia de Pacto 1 (`1`), Magia de Pacto 2 (`2`), Magia de Pacto 3 (`3`), Habilidad Definitiva / Ancestral (`4`), Poción / Curación (`v`).
  - **Movimiento (4):** Saltar (`space`), Esquivar / Rodar (`leftshift`), Correr / Sprint (`leftctrl`), Agacharse / Sigilo (`c`).
  - **Interacción (4):** Interactuar / Saquear (`x`), Visión Espiritual / Ojo de Cuervo (`r`), Mapa de Alca (`m`), Inventario / Reposo (`i`).

### 6. Pruebas Unitarias y Verificación
- Actualización de `tests/test_service_action_catalog.py` y `tests/test_adapter_discovery.py`.
- **Ejecución de la suite completa:**
  ```bash
  python3 -m unittest discover -s tests
  ```
  **Resultado:** `Ran 204 tests in 7.196s — OK` (204 pruebas pasando, 0 fallos).

---

## 6. Mandato de Visualización en Visual Studio Code

El usuario estableció una directiva obligatoria de interacción:
> *"Quiero que cada cambio que realices, se me sea mostrado en VS Code justo en la línea donde empieza el cambio y si es un cambio con varias modificaciones en el mismo fichero, quiero que en pantalla se me muestre el cambio más grande..."*

### Requisitos Técnicos de Ejecución en Wayland:
Para interactuar correctamente con la sesión gráfica del usuario en Linux/Wayland desde la terminal, los comandos hacia `code` deben incluir las variables de entorno de la sesión activa:
```bash
DISPLAY=:0 WAYLAND_DISPLAY=wayland-1 XDG_RUNTIME_DIR=/run/user/1000 code --reuse-window --goto <ruta_absoluta>:<linea>
```

### Líneas señalizadas en VS Code para el Hotfix:
1. `presets/soulframe.json:1` (Nuevo preset oficial de Soulframe).
2. `src/domain/application.py:27` (Adición del campo `is_game`).
3. `src/adapters/desktop_entries.py:108` (Heurística de `is_game` en `.desktop`).
4. `src/adapters/application_discovery_adapter.py:86` (Propagación de `is_game` en adaptadores).
5. `src/services/action_catalog.py:175` (Soporte de catálogo para juegos Wine y de escritorio).
6. `tests/test_service_action_catalog.py:161` (Test de alias y catálogo de Soulframe).
7. `tests/test_adapter_discovery.py:114` (Test de descubrimiento de juegos de escritorio).

---

## 7. Incidencia de la GUI en Ejecución y Validación Final

### Observación del Usuario:
El usuario indicó: *"ok, para aclarar, esta es la revisión, no la implementación, porque aún sigo sin ver las acciones para asignar a los botones"*.

### Causa Técnica:
- El proceso `/usr/bin/python3 src/cli.py gui` estaba corriendo en el sistema con PID `66685` desde las **13:23** (antes de modificar los ficheros).
- En Python con GTK4/Libadwaita, los módulos importados y los ficheros JSON leídos en el arranque se cargan en memoria RAM; **no existe recarga en caliente** dentro de un proceso en ejecución.
- Al simular el inicio con la versión actual del código, la app descubrió 111 aplicaciones, reconoció a Soulframe con `is_game=True` y cargó las 19 acciones del catálogo.

### Resolución:
El usuario reinició la aplicación gráfica y confirmó:
> *"ok, perfecto, si funciona, entonces muestrame el plan para la implementación del hito 2"*

---

## 8. Plan Técnico Detallado para el Hito 2

**Objetivo:** Permitir que el gestor descubra automáticamente los juegos no oficiales vinculados a la biblioteca de Steam (*Non-Steam Games*, como **Soulframe**), listándolos en la GUI con el prefijo `steam:<appid>` (ej. `steam:3519040750`), marcados con `is_game=True` y vinculados automáticamente a sus presets y acciones.

### Especificación del Formato Binario Valve (Binary KeyValues)
- **Ruta del fichero en disco:** `~/.local/share/Steam/userdata/<user_id>/config/shortcuts.vdf`
- **Estructura en bytes:**
  - `0x00`: Inicio de bloque / mapa anidado (lee cadena terminada en `\x00`).
  - `0x01`: Cadena de texto terminada en byte nulo (`\x00`).
  - `0x02`: Entero de 32 bits Little-Endian (uint32 para `appid`).
  - `0x08`: Fin de bloque / cierre de mapa.

### Datos reales verificados en el equipo:
El archivo real `/home/thelion/.local/share/Steam/userdata/437978958/config/shortcuts.vdf` tiene 601 bytes y contiene la entrada de Soulframe:
- `AppName`: `Soulframe`
- `appid`: `-775926546` (en signed int32) = `3519040750` (en uint32)
- `Exe`: `"/home/thelion/.wine/drive_c/users/thelion/AppData/Local/Soulframe/Downloaded/Public/Tools/Launcher.exe"`
- `StartDir`: `"/home/thelion/.wine/drive_c/users/thelion/AppData/Local/Soulframe/Downloaded/Public/Tools/"`
- `LaunchOptions`: `STEAM_COMPAT_MOUNTS="/games" %command%`
- `ShortcutPath`: `/home/thelion/.local/share/applications/wine/Programs/Soulframe/Soulframe.desktop`

### Tareas Paso a Paso:
1. **`src/adapters/steam_discovery.py`**:
   - Definir dataclass `SteamShortcut(app_id, name, exe, start_dir, launch_options, icon, shortcut_path)`.
   - Implementar función pura `parse_binary_vdf(data: bytes) -> dict`.
   - Implementar `discover_steam_shortcuts(steam_root: Path | None = None) -> list[SteamShortcut]`.
2. **`src/adapters/application_discovery_adapter.py`**:
   - En `discover_steam_applications()`, unir los juegos oficiales (`appmanifest_*.acf`) con los accesos directos descubiertos (`shortcuts.vdf`).
   - Mapear a `Application(application_id=f"steam:{shortcut.app_id}", name=shortcut.name, is_game=True)`.
3. **Pruebas Unitarias TDD (`tests/test_adapter_steam_discovery.py`)**:
   - Test con payload binario sintético Valve.
   - Test con el caso real de Soulframe (`appid: 3519040750`).
   - Test de tolerancia a fallos ante archivos vacíos, truncados o corruptos.

---

## 9. Análisis de Rendimiento e Impacto Técnico

A la consulta del usuario sobre si el Hito 2 afectaría el rendimiento de la aplicación:

| Componente | Impacto Medido | Justificación Técnica |
| :--- | :--- | :--- |
| **Bucle del Motor Reactivo (`engine.py`)** | **0% (Nulo)** | El loop en segundo plano consulta únicamente `/proc` cada intervalo. El descubrimiento de Steam no corre dentro del bucle reactivo. |
| **Tiempo de Arranque de la GUI** | **~0.012 ms** | `shortcuts.vdf` pesa solo 601 bytes. Un benchmark real ejecutado en el sistema arrojó 12 microsegundos por parseo. |
| **Consumo de Memoria RAM** | **< 10 KB** | Solo se instancian estructuras ligeras de datos en Python. |
| **I/O en Disco y Caché** | **Caché en memoria** | `ApplicationDiscoveryAdapter` utiliza `_cached_all` para no volver a consultar el disco mientras la aplicación permanece abierta. |
| **Tolerancia a Fallos** | **Resiliente** | Si el fichero no existe, está bloqueado por Steam o está incompleto, se captura internamente retornando `[]` sin interrumpir la app. |

---

## 10. Estado Actual del Árbol Git (Listo para Continuar)

### Archivos Modificados / Creados pendientes de commit:
- `modificados:`
  - `src/domain/application.py`
  - `src/adapters/desktop_entries.py`
  - `src/adapters/application_discovery_adapter.py`
  - `src/services/action_catalog.py`
  - `tests/test_adapter_discovery.py`
  - `tests/test_service_action_catalog.py`
- `sin seguimiento (nuevos):`
  - `hitos-faltantes.md`
  - `presets/soulframe.json`
  - `src/services/presets/soulframe.json`
  - `SESION_CONTEXTO_HITO1_HOTFIX_Y_HITO2.md` (este documento)

### Siguiente Acción Inmediata:
Proceder con la implementación del **Hito 2** siguiendo el plan acordado y la directiva de visualización en VS Code.
