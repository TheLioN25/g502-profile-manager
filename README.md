# G502 Profile Manager

Administrador automático y manual de perfiles para el ratón **Logitech G502 HERO** en entornos Linux.

Permite conmutar automáticamente los perfiles de hardware del mouse (DPI, asignación de botones e iluminación) según la aplicación o videojuego que se encuentre en ejecución, utilizando [`ratbagctl`](https://github.com/libratbag/libratbag) (`libratbag`).

---

## Características

* 🔄 **Conmutación dinámica de perfiles:** Monitorea los procesos en tiempo real y activa el perfil correspondiente sin necesidad de intervención manual.
* 🎮 **Integración con Steam:** Detección automática de videojuegos instalados y en ejecución mediante la lectura de librerías VDF y manifiestos `.acf` (`steam:<appid>`).
* 🖥️ **Soporte para aplicaciones de escritorio:** Detección de aplicaciones basada en entradas `.desktop` estándar de Linux (XDG).
* ⚖️ **Sistema de prioridades:** Si varias aplicaciones configuradas están abiertas simultáneamente, se aplica el perfil de mayor prioridad.
* 🔙 **Restauración automática:** Si no hay ninguna aplicación configurada abierta (o al detener el motor con `Ctrl+C`), se restaura el perfil predeterminado de escritorio.
* ⌨️ **Interfaz CLI (`g502-profile`):** Herramienta de línea de comandos para explorar el catálogo de aplicaciones y gestionar su configuración.

---

## Requisitos

1. **Linux** con Python 3.10 o superior.
2. **libratbag / ratbagctl:** Debe estar instalado y el servicio `ratbagd` en ejecución.
   * **Debian / Ubuntu / Pop!_OS:**
     ```bash
     sudo apt install libratbag-tools ratbagd
     ```
   * **Arch Linux / Manjaro:**
     ```bash
     sudo pacman -S libratbag
     ```
   * **Fedora:**
     ```bash
     sudo dnf install libratbag-ratbagd
     ```
3. Verificar que el daemon esté activo y tu dispositivo sea detectado:
   ```bash
   sudo systemctl enable --now ratbagd
   ratbagctl list
   ```

---

## Estructura del Proyecto

```text
g502-profile-manager/
├── config.json              # Archivo de configuración persistente
├── src/
│   ├── engine.py            # Motor principal en segundo plano (bucle de monitoreo)
│   ├── cli.py               # Interfaz de línea de comandos (g502-profile)
│   ├── config_manager.py    # Carga, validación y persistencia de config.json
│   ├── application_catalog.py # Modelo de datos del catálogo de aplicaciones
│   ├── application_manager.py # Coordinación de catálogo y configuración
│   ├── application_resolver.py# Mapeo de procesos a aplicaciones detectadas
│   ├── desktop_entries.py   # Descubrimiento y análisis de archivos .desktop
│   ├── process_discovery.py # Exploración de procesos activos en el sistema
│   ├── process_classifier.py# Clasificación y filtrado de ejecutables
│   └── steam_discovery.py   # Detección de bibliotecas y juegos de Steam
└── README.md
```

---

## Configuración (`config.json`)

El archivo `config.json` define el ratón objetivo, el perfil predeterminado y las aplicaciones asociadas:

```json
{
    "device": "Logitech G502 HERO Gaming Mouse",
    "desktop_profile": 0,
    "check_interval": 2,
    "applications": [
        {
            "application_id": "steam:230410",
            "source": "steam",
            "profile": 2,
            "priority": 100
        }
    ]
}
```

* **`device`**: Nombre del dispositivo según la salida de `ratbagctl list`.
* **`desktop_profile`**: Índice del perfil de hardware a usar para el escritorio (por defecto: `0`).
* **`check_interval`**: Frecuencia de muestreo en segundos para evaluar procesos activos.
* **`applications`**: Lista de asociaciones entre aplicaciones y perfiles.
  * `application_id`: Identificador estable (ej. `steam:230410` para Warframe).
  * `source`: Origen de la aplicación (`steam` o `desktop`).
  * `profile`: Perfil del ratón que se activará.
  * `priority`: Nivel de prioridad ante múltiples aplicaciones concurrentes (número mayor = mayor prioridad).

---

## Uso

### 1. Iniciar el Motor Automático

Ejecuta el demonio de monitoreo continuo:

```bash
python3 src/engine.py
```

El motor validará que el mouse esté conectado, cargará la configuración y comenzará a vigilar los procesos. Al pulsar `Ctrl+C`, el motor restaurará el perfil del escritorio antes de cerrarse de forma segura.

### 2. Uso de la CLI (`g502-profile`)

La CLI permite inspeccionar y configurar aplicaciones desde la terminal:

* **Listar aplicaciones detectadas:**
  ```bash
  python3 src/cli.py list
  ```
  Muestra las aplicaciones encontradas en Steam/sistema, indicando cuáles ya están configuradas `[X]` con su perfil y prioridad, y cuáles no `[ ]`.

* **Configurar una aplicación:**
  ```bash
  python3 src/cli.py configure "<Nombre de la aplicación>"
  ```

* **Consultar ayuda y opciones:**
  ```bash
  python3 src/cli.py --help
  ```

---

## Estado del Proyecto

Actualmente en versión `0.2.0-dev`.
* ✅ Motor de detección y cambio automático completamente funcional.
* ✅ Integración con Steam y entradas `.desktop`.
* 🚧 CLI interactiva en desarrollo (comandos `configured`, `update`, `remove` y ejecución directa de `engine` vía CLI en progreso).
