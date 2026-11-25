# 🗺️ Hoja de Ruta: Arquitectura Multi-Dispositivo (Logitech G Suite)

Documento de diseño arquitectónico y especificación técnica para la futura evolución de **G502 Profile Manager** hacia una suite unificada de periféricos Logitech G en Linux (*Logitech G Device Manager* / *G-Stark Manager*).

---

## 🎯 1. Filosofía y Principio Innegociable: Aislamiento Total

El objetivo primordial de esta arquitectura es **escalar sin fragilidad**:
* **Cero contaminación cruzada:** El dominio, adaptadores y las 287 pruebas unitarias del G502 jamás se mezclan con la lógica de teclados, auriculares u otros dispositivos.
* **Profundidad modular:** Cada familia de periféricos opera en su propio submódulo aislado, con sus propias entidades, adaptadores de hardware y lienzo vectorial.
* **Sostenibilidad:** Si un dispositivo nuevo introduce un bug o cambia su protocolo, el resto de periféricos permanece 100% operativo y blindado.

---

## 🖥️ 2. Diseño de Interfaz de Usuario (UI/UX Unificada)

Se mantiene y reutiliza la arquitectura visual nativa en **GTK4 + Libadwaita (Tema Stark Tech)**:

### A. Navegación Lateral Global (Sidebar Izquierdo)
* **El contexto del juego es el rey:** La barra lateral de juegos y aplicaciones (`Gtk.Paned`) sigue siendo global.
* Al seleccionar un juego (ej. *Guild Wars 2*, *Warframe*, *Aion 2* o *Soulframe*), el sistema asocia de forma reactiva el perfil correspondiente a cada periférico conectado al mismo tiempo.

### B. Selector de Dispositivo en HeaderBar (Desplegable Persistente)
* El chip actual de estado:
  ```text
  [ 🖱️ ] 🟢 G502 HERO Connected
  ```
* Se transforma en un selector interactivo (`Gtk.DropDown` / `Gtk.MenuButton`):
  ```text
  ┌──────────────────────────────────────────────┐
  │ [ 🖱️ ] 🟢 G502 HERO (Ratón)           ✓     │
  │ [ ⌨️ ] 🟢 G915 LIGHTSPEED (Teclado)          │
  │ [ 🎧 ] 🟢 PRO X Wireless (Auriculares)       │
  └──────────────────────────────────────────────┘
  ```

### C. Lienzo Central Reactivo (Cairo Canvas)
* Al conmutar el dispositivo en el desplegable:
  * **Ratón activo:** Se renderiza el plano vectorial del G502 (`mouse_diagram.py`).
  * **Teclado activo:** Se renderiza el plano vectorial del teclado con sus teclas macro G dedicadas y rueda de volumen (`keyboard_diagram.py`).
  * **Auricular activo:** Se renderiza el panel de curvas de ecualización y nivel de batería.
* **Columna derecha (Acciones):** Se actualiza dinámicamente mostrando el catálogo de acciones aplicables a los botones o teclas del dispositivo seleccionado.

### D. Persistencia Absoluta de Estado
* **El estado reside en el Dominio en memoria:** La interfaz solo refleja los objetos de negocio.
* Editar botones del ratón y conmutar inmediatamente la pestaña al teclado **no pierde ni resetea datos**. Al volver al ratón, todo sigue en su lugar y se guarda de forma atómica en disco (`flock` + `RLock`).

---

## 🏗️ 3. Estructura de Backend y Árbol de Código

Aislamiento limpio dentro del estándar de empaquetado de Linux (`pyproject.toml`, AUR, Flatpak):

```text
src/
├── core/                         # Motor compartido y cimientos del sistema
│   ├── engine.py                 # Motor reactivo de detección de ventanas y procesos
│   ├── resolver.py               # Detección de Steam (.acf/.vdf), Proton y Wine
│   ├── storage.py                # Persistencia atómica JSON con respaldo anti-corrupción
│   └── tray.py                   # Bandeja del sistema D-Bus (StatusNotifierItem)
│
├── devices/                      # Cajas de arena independientes por dispositivo
│   ├── base.py                   # Interfaces abstractas: BaseDevice, DeviceCapabilities
│   │
│   ├── g502/                     # [MÓDULO G502 INTACTO]
│   │   ├── domain.py             # Entidades del ratón (Profile, Button, DpiStage)
│   │   ├── ratbag_adapter.py     # Adaptador libratbag / HID++ para el G502
│   │   └── mouse_diagram.py      # Diagrama vectorial 2D en Cairo
│   │
│   ├── keyboard/                 # [MÓDULO TECLADO AISLADO]
│   │   ├── domain.py             # Teclas G, modos de juego, iluminación por tecla
│   │   ├── keyboard_adapter.py   # Adaptador de hardware para teclados
│   │   └── keyboard_diagram.py   # Plano vectorial de distribución de teclado
│   │
│   └── headset/                  # [MÓDULO AUDIO AISLADO]
│       ├── domain.py             # Perfiles EQ, micrófono, sidetone
│       └── audio_adapter.py      # Adaptador de audio / batería
│
└── gui/                          # Capa de presentación GTK4 / Libadwaita
    ├── app.py                    # Ciclo de vida Gtk.Application
    ├── window.py                 # Ventana principal Stark Tech y Gtk.Paned
    ├── device_selector.py        # Menú desplegable en HeaderBar
    └── style.css                 # CSS zafiro, juntas láser y acento dual
```

---

## 💾 4. Esquema de Almacenamiento JSON Retrocompatible

Evolución del repositorio atómico `~/.config/g502-profiles.json` a esquema unificado:

```json
{
  "version": 2,
  "settings": {
    "theme_accent": "crimson",
    "auto_profile_enabled": true,
    "osd_notifications": true
  },
  "devices": {
    "g502_hero": {
      "active_profile_id": "guild_wars_2_dps",
      "profiles": [ ... ]
    },
    "g915_keyboard": {
      "active_profile_id": "guild_wars_2_keys",
      "profiles": [ ... ]
    }
  }
}
```

* **Retrocompatibilidad garantizada:** Si el archivo en disco viene en versión 1 (solo G502), se migra automáticamente encapsulando los perfiles existentes bajo la clave `devices.g502_hero` sin pérdida de datos.

---

## 🧪 5. Estrategia de Pruebas Unitarias

* **Suites independientes:**
  * `tests/test_device_g502.py` (Mantiene sus **287 tests** blindados al 100%).
  * `tests/test_device_keyboard.py` (Suite dedicada para teclados).
  * `tests/test_device_headset.py` (Suite dedicada para auriculares).
* **Mocks puros de hardware:** Cada periférico se prueba en milisegundos sin requerir el hardware físico conectado.

---

## 🚀 6. Potencial de Patrocinio / Alianza con Logitech

Si en algún momento surge contacto, financiamiento o patrocinio (comunitario o corporativo):
1. La arquitectura modular permite entregar una alternativa completa a G-HUB para todo el ecosistema de jugadores de Linux.
2. Cada dispositivo nuevo se incorpora como un módulo `devices/<modelo>` sin riesgo de regresiones.
3. El estándar de ingeniería (Clean Architecture, 100% Mutation Shielding y cero telemetría) posiciona este proyecto como el estándar de referencia en Linux.
