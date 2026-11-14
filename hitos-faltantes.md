# Hitos Faltantes — Soporte para Juegos No Oficiales y Accesos Directos (Soulframe / Wine / Steam)

Documento de contexto técnico que detalla los hitos pendientes de implementación en **Logitech G502 HERO Profile Manager** para completar el soporte integral de aplicaciones externas, juegos no oficiales (*Non-Steam Games*) y títulos ejecutados mediante Wine/Proton.

---

## Estado Actual y Antecedentes
* **Hito 1 (Implementado):**
  * Soporte para escaneo recursivo de entradas de escritorio (`rglob("*.desktop")`) en `src/adapters/desktop_entries.py`, permitiendo indexar subdirectorios como `~/.local/share/applications/wine/Programs/...`.
  * Extracción del ejecutable real de Windows y lectura de `StartupWMClass` en comandos delegados por Wine (`env ... wine "C:\..."` y enlaces `.lnk`).
  * Indexación combinada en `src/adapters/application_resolver.py` (`build_desktop_entry_index`) para que `launcher.exe` empareje con perfiles de escritorio.

A continuación se detallan los **dos hitos técnicos pendientes** para cerrar el ciclo de detección estática y dinámica.

---

## Hito 2: Soporte para Accesos Directos de Steam (`shortcuts.vdf`)

### 1. Objetivo
Permitir que el gestor descubra automáticamente juegos no oficiales que el usuario vincula en su biblioteca de Steam (como **Soulframe**), mostrándolos en la lista de aplicaciones de la GUI junto a los juegos oficiales de Valve.

### 2. Contexto del Sistema y Formato
* **Ubicación en disco:**  
  `~/.local/share/Steam/userdata/<user_id>/config/shortcuts.vdf`
* **Formato técnico:**  
  Steam almacena estos accesos directos en un formato binario propietario de Valve (Binary KeyValues), **no** en archivos de texto `.acf`.
  * `0x00`: Inicio de bloque / mapa anidado.
  * `0x01`: Cadena de texto terminada en byte nulo (`\x00`).
  * `0x02`: Entero de 32 bits Little-Endian (signed/unsigned `appid`).
  * `0x08`: Fin de bloque / mapa.
* **Estructura de datos interna de cada acceso directo:**
  ```python
  {
      "AppName": "Soulframe",
      "appid": -775926546,  # 3519040750 en uint32
      "Exe": '"/ruta/.../Launcher.exe"',
      "StartDir": '"/ruta/.../"',
      "LaunchOptions": 'STEAM_COMPAT_MOUNTS="/games" %command%',
      "icon": "61C0_Launcher.0",
      "ShortcutPath": "/ruta/.../Soulframe.desktop",
  }
  ```

### 3. Archivos a Modificar
* [src/adapters/steam_discovery.py](src/adapters/steam_discovery.py):
  * **Parser Binario VDF:** Implementar una función pura en Python (sin librerías externas) `parse_binary_vdf(stream_or_bytes)` que decodifique la estructura de `shortcuts.vdf`.
  * **Descubridor de shortcuts:** Implementar `discover_steam_shortcuts(steam_root: Path)` que itere sobre `userdata/*/config/shortcuts.vdf`.
  * **Estructura de dominio / datos:** Definir un dataclass `SteamShortcut(app_id, name, exe, launch_options)` o mapearlo a `SteamAppManifest` compatible.
* [src/adapters/application_discovery_adapter.py](src/adapters/application_discovery_adapter.py):
  * En `discover_steam_applications()`, invocar tanto el lector de manifiestos oficiales (`discover_installed_steam_apps`) como el nuevo lector de shortcuts, unificando bajo identificadores estables `steam:<app_id>`.

### 4. Pruebas Unitarias Requeridas
* Test con payload binario sintético de `shortcuts.vdf` para verificar la decodificación de `AppName`, `appid`, `Exe` y `LaunchOptions`.
* Test de tolerancia a fallos ante archivos `shortcuts.vdf` truncados, corruptos o vacíos.
* Test de integración en `TestApplicationDiscoveryAdapter` comprobando que los juegos de shortcuts se listen en el selector.

---

## Hito 3: Resolución Dinámica de Procesos (Lanzador vs. Binario Real)

### 1. Problema Técnico
En juegos como Soulframe (y muchos títulos de Wine/Steam):
1. El acceso directo registrado apunta al lanzador:  
   `.../Tools/Launcher.exe` (o `StartupWMClass=launcher.exe`).
2. Una vez que el usuario presiona "Jugar", el launcher se cierra o pasa a segundo plano y se ejecuta el binario real del juego:  
   `/games/Games/Soulframe/Downloaded/Downloaded/Public/Soulframe.x64.exe`.
3. El motor reactivo (`src/engine.py`), al escanear `/proc`, ve activo el proceso `Soulframe.x64.exe`. Al no encontrar una coincidencia exacta con el ejecutable registrado (`launcher.exe`), asume que el juego se cerró y restaura el perfil `desktop:general`.

### 2. Soluciones Técnicas Propuestas

#### Opción A: Mapeo de Ejecutables Secundarios / Binarios Conocidos (Recomendada por simplicidad)
* Permitir en el perfil o en un catálogo de extensiones asociar ejecutables secundarios al perfil principal.
* Por ejemplo: Si el perfil está asignado a `desktop:launcher.exe` o `steam:3519040750`, permitir especificar una lista de ejecutables asociados: `["Soulframe.x64.exe", "Soulframe.exe"]`.
* En [src/adapters/application_resolver.py](src/adapters/application_resolver.py): Indexar también estos binarios alternativos para que activen el mismo perfil.

#### Opción B: Heurística por Ruta de Instalación o Subárbol de Procesos
* Similar a lo implementado en [src/adapters/epic_discovery.py](src/adapters/epic_discovery.py):
  * Si un proceso en `/proc` corre bajo el mismo árbol de directorios donde reside el ejecutable del shortcut/desktop (ej. `/games/Games/Soulframe/...`), resolverlo a esa aplicación.
  * O bien, inspeccionar el `PPID` (proceso padre) para detectar cuándo un proceso Windows es hijo del lanzador o del supervisor de Steam (`reaper` / `pressure-vessel`).

### 3. Archivos a Modificar
* [src/domain/profile.py](src/domain/profile.py) (si se añade campo de ejecutables secundarios/alias) o [src/adapters/application_resolver.py](src/adapters/application_resolver.py).
* [src/engine.py](src/engine.py): Ajuste fino para evitar conmutaciones espurias (*flapping*) durante la transición entre el cierre del launcher y la apertura del juego principal.

---

## Resumen del Checklist de Implementación

- [x] **Hito 1:** Detección recursiva de `.desktop`, soporte `StartupWMClass` y comandos Wine (Completado).
- [x] **Hito 2:**
  - [x] Implementar parser binario de KeyValues en `src/adapters/steam_discovery.py`.
  - [x] Lectura de `~/.local/share/Steam/userdata/*/config/shortcuts.vdf`.
  - [x] Exponer shortcuts como aplicaciones `steam:<id>` en `src/adapters/application_discovery_adapter.py`.
  - [x] Tests unitarios con mocks para `shortcuts.vdf`.
- [x] **Hito 3:**
  - [x] Mecanismo de resolución para `Soulframe.x64.exe` (alias de proceso o heurística de directorio).
  - [x] Verificación en `src/adapters/application_resolver.py` y `src/engine.py`.
  - [x] Tests unitarios de resolución de procesos hijos/juegos Wine.
- [x] **Hito 4:**
  - [x] Verificación final de la suite completa (`python3 -m unittest discover -s tests`).
  - [x] Generación de `brief.md` para revisión cruzada con OpenCode (Regla 11) si aplica.
