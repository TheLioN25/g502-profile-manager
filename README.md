# Logitech G502 HERO Profile Manager (Linux)

Administrador avanzado de perfiles y automatización en tiempo real para el ratón **Logitech G502 HERO** en entornos Linux.

Permite configurar visualmente los botones, macros, sensibilidades (DPI) y zonas de iluminación LED del ratón, además de conmutar automáticamente los perfiles de hardware según el videojuego o aplicación activa en el sistema mediante [`ratbagctl`](https://github.com/libratbag/libratbag) (`libratbag`).

---

## 🌟 Características Principales

* 🎨 **Interfaz Gráfica Moderna (GTK4 + Libadwaita):**
  * Diseño nativo para Linux con soporte de tema oscuro automático.
  * **Barra lateral con gestor de aplicaciones en dos secciones:**
    * **Sección Superior (Configuradas):** Acceso rápido y prioritario a las aplicaciones que ya tienen perfiles configurados (ej. *Escritorio / Sistema*, *Warframe*, *Guild Wars 2*).
    * **Línea divisoria y buscador reactivo:** Barra de búsqueda ubicada estratégicamente sobre las aplicaciones pendientes de configuración.
    * **Sección Inferior (No configuradas):** Catálogo de juegos y aplicaciones instaladas en el sistema, filtrables al vuelo para configurar nuevos títulos.
  * **Interruptor Auto-Perfil (⚡) en la cabecera (HeaderBar):** Permite encender o apagar la auto-detección reactiva directamente desde la interfaz gráfica, manteniendo la GUI 100% fluida en un hilo secundario y mostrando el juego activo y sus DPI en tiempo real en la cabecera.
  * **Plano interactivo vectorial del ratón** renderizado en tiempo real con Cairo Canvas: muestra asignaciones de botones, tooltips informativos y sincronización visual con el color LED configurado.
  * Gestión multi-perfil por aplicación: crear, duplicar, renombrar, eliminar y marcar perfiles predeterminados.
  * Selector de acciones con categorías temáticas (*Combate, Armas, Profesión, Movimiento, Productividad*) y asignación rápida de teclas personalizadas.
  * Aplicación instantánea al hardware con ejecución en segundo plano y debouncing para evitar bloqueos de la interfaz.

* 🔄 **Motor de Automatización Reactivo (`engine.py`):**
  * Monitoreo continuo y ligero de procesos activos en segundo plano (vía CLI o interruptor en la GUI).
  * **Descubrimiento unificado de aplicaciones:**
    * 🎮 **Steam:** Detección de juegos instalados y activos mediante lectura de librerías VDF y manifiestos `.acf` (`steam:<appid>`).
    * ⚔️ **Epic Games:** Detección automática en lanzadores Linux (Heroic Games Launcher, Legendary y Lutris).
    * 🖥️ **Escritorio Linux:** Integración con entradas `.desktop` estándar del sistema (XDG).
  * **Restauración Inteligente:** Al cerrar un juego, detener el motor o apagar el interruptor, se restaura automáticamente el perfil de **Escritorio / Sistema** (`desktop:general`).

* 🛡️ **Aislamiento Total de Perfiles (Modelo G-HUB):**
  * Resuelve la persistencia indeseada en la memoria física EEPROM del ratón.
  * Cualquier botón no asignado en un perfil se restablece automáticamente a su función de fábrica (*Back, Forward, DPI Shift, Profile Cycle*), evitando que configuraciones de un juego afecten al escritorio u otros títulos.

* 🧩 **Catálogos y Presets Modulares (`presets/`):**
  * Presets integrados en formato JSON ampliables para juegos como **Warframe** y **Guild Wars 2** (incluyendo mecánicas de profesión F1–F5 y habilidades personalizables), además de atajos de productividad para el escritorio.

* 🧪 **Suite de Pruebas Exhaustiva:**
  * 99 pruebas unitarias automatizadas con cobertura en dominio, persistencia, adaptadores de hardware y lógica de interfaz gráfica.

---

## 🏗️ Arquitectura del Proyecto

El proyecto está diseñado bajo principios de **Domain-Driven Design (DDD)** y **Clean Architecture**, asegurando un desacoplamiento estricto entre la lógica de negocio, los controladores de hardware y la interfaz de usuario:

```text
g502-profile-manager/
├── presets/                     # Manifiestos JSON de presets por juego/aplicación
│   ├── desktop_general.json
│   ├── steam_1284210_guildwars2.json
│   └── steam_230410_warframe.json
├── src/
│   ├── domain/                  # Entidades de dominio puro (sin dependencias externas)
│   │   ├── application.py       # Entidad Application y Value Object Action
│   │   ├── button.py            # Definición e invariantes de botones del G502
│   │   ├── dpi.py               # Configuración y validación de rangos de DPI
│   │   └── profile.py           # Agregado Profile y reglas de asignación
│   ├── services/                # Servicios de aplicación y orquestación
│   │   ├── action_catalog.py    # Gestión de catálogos y presets modulares
│   │   └── profile_manager.py   # Casos de uso de gestión y persistencia de perfiles
│   ├── storage/                 # Capa de infraestructura y almacenamiento
│   │   └── profile_repository.py# Repositorio JSON con recarga dinámica
│   ├── adapters/                # Adaptadores para sistemas externos y hardware
│   │   ├── ratbag_adapter.py    # Comunicación con libratbag/ratbagctl y aislamiento EEPROM
│   │   └── application_discovery_adapter.py # Descubrimiento unificado (Steam + Epic + Desktop)
│   ├── gui/                     # Capa de presentación GTK4 / Libadwaita
│   │   ├── app.py               # Punto de entrada de la aplicación gráfica
│   │   ├── window.py            # Ventana principal y control de eventos
│   │   ├── dialogs.py           # Diálogos modales (ActionPicker, NewProfile)
│   │   ├── mouse_diagram.py     # Canvas vectorial interactivo en Cairo
│   │   └── style.css            # Estilos Adwaita personalizados
│   ├── engine.py                # Demonio de automatización en tiempo real
│   ├── cli.py                   # Herramienta de línea de comandos
│   ├── steam_discovery.py       # Parser de VDF / ACF de Steam
│   ├── epic_discovery.py        # Descubrimiento de juegos de Epic Games
│   ├── desktop_entries.py       # Parser de archivos .desktop de Linux
│   └── process_discovery.py     # Inspección de procesos del sistema
└── tests/                       # Suite de 99 pruebas unitarias
```

---

## 📋 Requisitos del Sistema

1. **Linux** con Python 3.10 o superior.
2. **libratbag / ratbagctl:** Servicio de configuración de ratones para Linux.
3. **Bibliotecas de interfaz gráfica:** GTK4, Libadwaita y PyGObject.

### Instalación de dependencias

* **Debian / Ubuntu / Pop!_OS:**
  ```bash
  sudo apt install libratbag-tools ratbagd python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 python3-cairo
  ```

* **Arch Linux / Manjaro:**
  ```bash
  sudo pacman -S libratbag python-gobject gtk4 libadwaita python-cairo
  ```

* **Fedora:**
  ```bash
  sudo dnf install libratbag-ratbagd python3-gobject gtk4 libadwaita python3-cairo
  ```

### Habilitar el servicio del ratón
Asegúrate de que el demonio `ratbagd` esté iniciado y tu G502 sea reconocido:
```bash
sudo systemctl enable --now ratbagd
ratbagctl list
```

---

## 🚀 Guía de Uso

### 1. Interfaz Gráfica (Recomendado)
Para abrir el administrador visual con el plano interactivo del ratón:
```bash
python3 src/gui/app.py
```
* **Organizador de aplicaciones:** Explora las aplicaciones ya configuradas en la sección superior o utiliza el buscador para configurar títulos nuevos desde la sección inferior.
* **Interruptor Auto-Perfil (⚡):** Enciende el switch en la barra superior para activar la supervisión de procesos en segundo plano. Detectará cuando entres o salgas de tus juegos y aplicará o restaurará los perfiles en tiempo real sin congelar la ventana.
* **Personalización Completa:** Ajusta los DPI, el color LED o haz clic en cualquier botón del esquema interactivo para asignarle una acción del catálogo o una tecla personalizada.
* **Aplicar al ratón:** Graba instantáneamente la configuración en la memoria física del ratón.

### 2. Motor de Automatización en Segundo Plano
Para activar el cambio automático de perfiles al abrir o cerrar juegos:
```bash
python3 src/engine.py
```
* El motor detectará automáticamente el lanzamiento de juegos compatibles (ej. Warframe, Guild Wars 2) y aplicará su perfil asignado.
* Al salir del juego o detener el motor con `Ctrl+C`, se restablecerá automáticamente el perfil de **Escritorio / Sistema**.

### 3. Interfaz de Línea de Comandos (CLI)
Para consultar o gestionar aplicaciones desde la terminal:
```bash
# Listar aplicaciones detectadas y estado de configuración
python3 src/cli.py list

# Ver ayuda general
python3 src/cli.py --help
```

---

## 🎮 Compatibilidad en Juegos (Steam / Proton / Wayland)

Si juegas títulos de Windows en Linux mediante **Steam Play / Proton**:
* Se recomienda utilizar versiones estables como **Proton 10** o **Proton Experimental**.
* Si ejecutas un juego bajo Wayland (ej. KDE Plasma o GNOME) con versiones personalizadas de Wine/Proton y notas que las teclas compuestas del ratón no se registran en el juego, añade el siguiente parámetro en las **Opciones de lanzamiento** de Steam del juego:
  ```bash
  PROTON_ENABLE_WAYLAND=0 %command%
  ```
  *(O junto con MangoHud: `PROTON_ENABLE_WAYLAND=0 mangohud %command%`)*. Esto garantiza que las señales de teclado del ratón viajen de forma directa y sin interferencias a través de la capa XWayland.

---

## 🧪 Ejecución de Pruebas Unitarias

Para ejecutar la suite completa de 99 pruebas automatizadas:
```bash
python3 -m unittest discover -s tests -v
```
Las pruebas validan invariantes de dominio, persistencia atómica en disco, sincronización de hardware mediante mocks y la lógica de la interfaz gráfica sin requerir hardware físico conectado.

---

## 📄 Licencia

Proyecto privado desarrollado para optimización de periféricos Logitech en Linux.
