# 🚀 Reddit Post Template — Logitech G502 HERO Profile Manager (v1.0.0 Release)

> **Nota:** Este archivo contiene el borrador listo para copiar y pegar en Reddit, con sugerencias de títulos, tags/flairs, subreddits recomendados, y el desglose técnico detallado de todos los commits realizados para esta versión v1.0.0.

---

## 🎯 Subreddits Recomendados & Flairs

1. **r/G502Masterrace** — Flair: `Software` / `Discussion` *(Comunidad dedicada y apasionada exclusivamente por el Logitech G502)*
2. **r/LogitechG** — Flair: `Software` / `Discussion` *(Comunidad de Logitech que usa Linux y sufre la falta de G-HUB nativo)*
3. **r/linuxgaming** — Flair: `Release` / `Project` *(Audiencia de jugadores en Linux con Wine/Proton/Steam)*
4. **r/linux** — Flair: `Software` / `Release` *(Entusiastas del escritorio Linux y aplicaciones GTK4/Libadwaita)*
5. **r/unixporn** — Flair: `Tool` / `Workflow` *(Por el diseño futurista Stark Tech / Libadwaita y la integración visual)*

---

## 💡 Sugerencias de Títulos para el Post

- **Opción 1 (Directa y atractiva):**
  > `[Release] Logitech G502 Profile Manager v1.0.0 for Linux is here: Reactive Auto-Switching, GTK4 Stark Tech UI, Wine/Proton support & 100% Mutation Tested`
- **Opción 2 (Enfocada en resolver el dolor de G-HUB):**
  > `Tired of G-HUB not working on Linux? I built an open-source, reactive G502 Profile Manager in GTK4 with Steam/Wine game detection and Stark Tech aesthetic (v1.0.0)`
- **Opción 3 (Comunidad hispana):**
  > `[Lanzamiento v1.0.0] Administrador de perfiles y auto-conmutación reactiva para Logitech G502 en Linux (GTK4 + Libadwaita)`

---

# 🇺🇸 Versión en Inglés (Post Principal para Reddit)

```markdown
Hey everyone! 👋

I'm excited to share the official **v1.0.0 release** of **Logitech G502 Profile Manager**, an open-source, native hardware profile manager and real-time reactive automation engine for Logitech G502 mice on Linux!

If you've ever missed Logitech G-HUB's automatic game profile switching or wanted deep hardware control without clunky web apps or missing Linux drivers, this project is built for you.

---

### 🌟 What is this project?

It's a native **GTK4 + Libadwaita** application built with Clean Architecture, Domain-Driven Design (DDD), and powered by the standard Linux driver `libratbag` (`ratbagctl`). It allows full hardware-level button remapping, DPI stages, RGB LIGHTSYNC control, and background game detection with **zero desktop stutter**.

* **📅 Project Maturity & Timeline:**
  * Initial development started in **July 2026**.
  * Publicly released on GitHub on **September 12, 2026**.
  * Reached the milestone **v1.0.0 official release on November 22, 2026** after months of active dogfooding and architecture hardening.

---

### 🔥 What's New in v1.0.0?

#### 1. 🛡️ Futuristic "Stark Tech" Visual Overhaul & Original Cairo Blueprints
* **100% Original Vector Mouse Blueprint (Legal & DMCA-Safe):**
  * Rather than copying Logitech's proprietary diagrams, renders, or marketing assets (which are strictly Logitech's intellectual property and would create copyright/DMCA liability), we proactively designed and coded an **original 2D vector technical blueprint from scratch** directly in Python using the **Cairo graphics engine** (`src/gui/mouse_diagram.py`).
  * Features real-time reactive RGB illumination, dynamic DPI indicators, interactive hover hitboxes, and button binding callouts.
* **Official App Icon Redesign:** The classic application icon now wears a sharp Stark Tech crimson armor trim, perfectly matching the desktop chasis and theme aesthetics across all resolutions (from 512px down to 16px).
* **Metallic 3D Alloy Panels:** Redesigned Action Rows, Combo Rows, and Preference Groups with subtle laser chamfers, metallic sapphire gradients, and interactive hover glow.
* **Dual Energy Accent Switcher (Hot-Swappable):**
  * 🔴 **Iron Man Crimson (Stark Tech):** High-contrast neon crimson laser energy seams and active glows.
  * 🌐 **J.A.R.V.I.S. Cyan (Cyberpunk):** Sleek holographic cyan energy aesthetic.
  * Switch between energy accents instantly on the fly with the HeaderBar button (`settings.theme_accent`), fully persistent across restarts!
* **Modern Typography:** Integrated **Plus Jakarta Sans** with clean native fallbacks (`system-ui, -apple-system, sans-serif`).
* **Visual Precision:** Headings (*Laterals*, *Top Buttons*, *Scroll Wheel*, *DPI*, *RGB*) are pixel-aligned with the row indicators (`>`).
* **Resizable Application Sidebar:** Integrated vertical `Gtk.Paned` divider to resize your configured game profiles vs the full installed application catalog.

#### 2. ⚡ Game Detection & Reactive Engine
* **Steam & Non-Steam Support:** Parses native `.acf` manifests and binary Valve KeyValues (`shortcuts.vdf`) to detect both store games and custom Non-Steam launchers.
* **Wine / Proton & Dedicated Launchers:** Dynamic child process resolution with an **anti-flapping grace window (3.0s)** to prevent EEPROM stress and profile thrashing during game boot.
* **Epic Games & Lutris:** Out-of-the-box discovery across Heroic, Legendary, and Lutris.
* **Smart Fallback:** Automatically restores your `Desktop / System` profile the instant you exit a game or stop the engine.

#### 3. 🛡️ G-HUB Hardware Isolation & 1:1 Anti-Cheat Compliance
* **Clean State:** Any button not assigned in a profile automatically reverts to hardware factory defaults, eliminating key bleed between games and desktop.
* **Anti-Cheat Safe:** Strict 1:1 hardware mapping. Zero timed loops or synthetic macros that could trigger BattlEye, Easy Anti-Cheat, or Vanguard.

#### 4. 🔔 Pure D-Bus System Tray (StatusNotifierItem)
* Native integration with GNOME and KDE Plasma over pure session D-Bus (zero legacy GTK 3 `AppIndicator3` crashes).
* Real-time tooltip with active profile, battery level, active DPI stage, and engine status.

#### 5. 🧪 100% Mutation Tested (287 Unit Tests)
* The entire codebase (28/28 modules) is verified with mutation testing and passes **287 automated unit tests** (`OK (0 failures, 0 errors)`), covering domain logic, binary VDF parsers, async threading, D-Bus interfaces, and UI rendering.

---

### 📸 Screenshots

- **Main Window (Stark Tech Theme):** [View Screenshot](https://github.com/TheLioN25/g502-profile-manager/blob/master/docs/images/01_main_window.png)
- **Multi-Profile Management:** [View Screenshot](https://github.com/TheLioN25/g502-profile-manager/blob/master/docs/images/02_multi_profiles.png)
- **Action Picker & Binding:** [View Screenshot](https://github.com/TheLioN25/g502-profile-manager/blob/master/docs/images/04_action_assignment.png)

---

### 💻 How to Install & Run

#### Prerequisites
- Linux with Python 3.10+
- `libratbag` (`ratbagd` / `ratbagctl`)
- GTK4 and Libadwaita (`python3-gi`, `gir1.2-adw-1`, `gir1.2-gtk-4.0`)

```bash
# Clone the repository
git clone https://github.com/TheLioN25/g502-profile-manager.git
cd g502-profile-manager

# Verify the test suite
python3 -m unittest discover -s tests -v

# Launch the GTK4 GUI
python3 src/cli.py gui

# Or run the reactive auto-switcher in console/background
python3 src/cli.py auto
```

---

### 🔗 Project Links

* **GitHub Repository:** [https://github.com/TheLioN25/g502-profile-manager](https://github.com/TheLioN25/g502-profile-manager)
* **Architecture & C4 Diagrams:** [docs/ARCHITECTURE.md](https://github.com/TheLioN25/g502-profile-manager/blob/master/docs/ARCHITECTURE.md)
* **Changelog:** [CHANGELOG.md](https://github.com/TheLioN25/g502-profile-manager/blob/master/CHANGELOG.md)

Feedback, bug reports, and PRs are very welcome! If you have a different G502 variant (Proteus, LIGHTSPEED, G502 X), we'd love your feedback on device calibration!
```

---

# 🇪🇸 Versión en Español (Para Comunidades Hispanas)

```markdown
¡Hola a todos! 👋

Les comparto el lanzamiento oficial de la **versión v1.0.0** de **Logitech G502 Profile Manager**, un administrador de perfiles de hardware y motor de automatización reactiva nativo para ratones Logitech G502 en Linux.

Para quienes extrañan la conmutación automática de perfiles de Logitech G-HUB o buscan una herramienta nativa sin depender de aplicaciones web pesadas ni software propietario, este proyecto fue creado para solucionar exactamente eso.

---

### 🌟 ¿Qué es este proyecto?

Es una aplicación nativa en **GTK4 + Libadwaita** diseñada bajo arquitectura limpia (Clean Architecture / DDD) y apoyada en el demonio estándar de Linux `libratbag` (`ratbagctl`). Permite configurar botones, macros, niveles de DPI, iluminación RGB LIGHTSYNC y detección automática de juegos en segundo plano con **cero tirones en el escritorio**.

* **📅 Cronología y Madurez del Proyecto:**
  * Desarrollo iniciado a principios de **julio de 2026**.
  * Publicado en GitHub el **12 de septiembre de 2026**.
  * Versión oficial **v1.0.0 lanzada el 22 de noviembre de 2026** tras meses de pruebas reales y endurecimiento arquitectónico.

---

### 🔥 Novedades de la versión v1.0.0

1. **Diseño Visual "Stark Tech" y Plano Vectorial Original (Cairo):**
   * **Plano Vectorial 100% Original (Blindado contra reclamos legales / DMCA):**
     * En lugar de copiar los esquemas o renders propietarios de Logitech (los cuales son propiedad intelectual exclusiva de Logitech Corporation y acarrearían infracciones de copyright o disputas legales), diseñé y programé de manera proactiva un **plano técnico vectorial 2D desde cero** directamente en código Python utilizando el motor gráfico **Cairo** (`src/gui/mouse_diagram.py`).
     * Soporta renderizado de iluminación RGB dinámica en vivo, selector reactivo de DPI, áreas interactivas al pasar el cursor y visualización directa de asignaciones por botón.
   * **Nuevo icono oficial:** El icono de la aplicación se viste con una moldura de armadura carmesí sólida Stark Tech en todas sus resoluciones (desde 512px hasta 16px y SVG).
   - Chasis con degradado azul zafiro oscuro y biseles metálicos con estética de armadura 3D.
   - **Sistema de Acento de Energía Dual (Intercambiable en caliente):**
     - 🔴 **Carmesí Iron Man (Stark Tech):** Líneas de división láser en rojo carmesí neón.
     - 🌐 **Cian J.A.R.V.I.S. (Cyberpunk):** Estética holográfica en cian tecnológico.
     - Persistencia atómica de la preferencia de color en disco (`settings.theme_accent`).
   - **Tipografía moderna:** Integración de **Plus Jakarta Sans** con degradación nativa al sistema.
   - **Alineación geométrica:** Sangría perfecta de títulos y descripciones con los indicadores de botón (`>`).
   - **Divisor redimensionable en barra lateral:** `Gtk.Paned` interactivo para ajustar la proporción entre perfiles configurados y catálogo de apps.

2. **Detección reactiva de juegos y lanzadores:**
   - Steam oficial (`.acf`) y accesos directos No-Steam (`shortcuts.vdf` binario puro de Valve).
   - Juegos de Wine / Proton con resolución de procesos hijos y ventana anti-flapping de 3.0s (evita estrés en la EEPROM del ratón durante el inicio del juego).
   - Detección para Heroic, Legendary y Lutris (Epic Games).
   - Restauración automática del perfil de Escritorio al cerrar juegos o pausar el motor.

3. **Aislamiento de hardware (Modelo G-HUB) y seguridad Anti-Cheat:**
   - Botones sin asignar en un perfil regresan automáticamente a valores de fábrica, evitando que queden teclas pegadas de un juego al salir al escritorio.
   - Mapeo 1:1 estricto de hardware; sin bucles ni macros continuas que puedan detonar falsos positivos en Easy Anti-Cheat o BattlEye.

4. **Bandeja del sistema nativa en D-Bus (StatusNotifierItem):**
   - Compatible al 100% con GNOME y KDE Plasma sin colisiones de memoria ni librerías obsoletas (adiós `AppIndicator3`).

5. **287 Pruebas Unitarias y Blindaje Total contra Mutaciones:**
   - Cobertura integral probada contra mutaciones en sus 28 módulos con 287 tests pasando al 100%.

---

### 💻 Instalación y Ejecución Rápida

```bash
# Clonar el repositorio
git clone https://github.com/TheLioN25/g502-profile-manager.git
cd g502-profile-manager

# Comprobar los tests
python3 -m unittest discover -s tests -v

# Iniciar la interfaz gráfica
python3 src/cli.py gui

# O iniciar el motor en terminal
python3 src/cli.py auto
```

* **Repositorio:** [https://github.com/TheLioN25/g502-profile-manager](https://github.com/TheLioN25/g502-profile-manager)
```

---

## 📋 Trazabilidad de Commits Realizados para v1.0.0

A continuación se detalla la secuencia de commits locales que componen esta actualización hacia la versión oficial v1.0.0:

| Commit | Tipo / Mensaje Semántico | Descripción del Cambio Técnico |
| :---: | :--- | :--- |
| [`151992f`](https://github.com/TheLioN25/g502-profile-manager/commit/151992f) | `fix(cli): actualizar fallback de iconos png en pixmaps para barra de tareas en kde plasma (v1.0.0)` | Instalación y reemplazo de iconos rasterizados en `~/.local/share/pixmaps/` para asegurar que el gestor de tareas de KDE Plasma muestre el nuevo icono de inmediato. |
| [`08d7d88`](https://github.com/TheLioN25/g502-profile-manager/commit/08d7d88) | `style(icons): actualizar icono oficial con borde solido de armadura carmesi stark tech (v1.0.0)` | Regeneración de toda la familia de iconos (SVG y PNGs de 16 a 512px) con borde sólido carmesí Stark Tech e instalación en el sistema. |
| [`adee615`](https://github.com/TheLioN25/g502-profile-manager/commit/adee615) | `style(gui): integrar tipografia moderna Plus Jakarta Sans con degradacion nativa (v1.0.0)` | Descarga e instalación de la fuente en `~/.local/share/fonts/`, actualización de caché `fc-cache -f` y configuración en CSS global con fallback. |
| [`bc70515`](https://github.com/TheLioN25/g502-profile-manager/commit/bc70515) | `style(gui): alinear sangria de titulos y descripciones con iconos de recuadros (v1.0.0)` | Ajuste de sangría en `preferencesgroup box.header` con `margin-left: 14px;` para alinear títulos con el glifo `>` de cada botón. |
| [`3f235da`](https://github.com/TheLioN25/g502-profile-manager/commit/3f235da) | `feat(gui): incorporar selector de acento de energia carmesi iron man y cian jarvis con persistencia (v1.0.0)` | Botón dinámico en el HeaderBar para conmutar temas (`theme-crimson` vs `theme-cyan`), persistencia atómica en repositorio JSON y prueba unitaria. |
| [`094d6a3`](https://github.com/TheLioN25/g502-profile-manager/commit/094d6a3) | `style(gui): refinar recuadros de accion, tarjetas de preferencias y chips en estilo stark tech (v1.0.0)` | Rediseño de `ActionRow` y `ComboRow` en aleación 3D, relieves metálicos, chips de estado tipo píldora y subtítulos con ID de botón. |
| [`bdea016`](https://github.com/TheLioN25/g502-profile-manager/commit/bdea016) | `feat(gui): implementar redimensionamiento vertical en sidebar y suprimir borde residual de cabecera (v1.0.0)` | Implementación de `Gtk.Paned` vertical para redimensionar la lista de juegos configurados y eliminación de bordes residuales en cabecera. |
| [`f152224`](https://github.com/TheLioN25/g502-profile-manager/commit/f152224) | `style(gui): remover linea roja bajo el encabezado y agregar separador laser sobre lista de juegos` | Calibración de divisiones de energía para dar limpieza visual y enfoque a la lista de juegos y navegación. |
| [`2526f0b`](https://github.com/TheLioN25/g502-profile-manager/commit/2526f0b) | `style(gui): incorporar divisiones de energia laser carmesi en sidebar, header y base de pestanas (v1.0.0)` | Integración de separadores sutiles estilo haz láser de energía (`laser-divider`). |
| [`00d8f3d`](https://github.com/TheLioN25/g502-profile-manager/commit/00d8f3d) | `style(gui): calibrar punto medio de azul zafiro, restaurar juntas rojas y estilizar botones en azul metalico (v1.0.0)` | Ajuste del degradado azul zafiro de fondo, biseles de juntas energéticas y botones con acabado metálico. |
| [`f8372d5`](https://github.com/TheLioN25/g502-profile-manager/commit/f8372d5) | `fix(gui): calibrar profundidad del degradado azul zafiro y sutileza en separadores laser (v1.0.0)` | Ajuste de saturación y brillo en los gradientes de ventana para evitar fatiga visual y mantener legibilidad. |
| [`32799bc`](https://github.com/TheLioN25/g502-profile-manager/commit/32799bc) | `feat(gui): implementar tema visual Stark Tech con chasis zafiro y juntas laser carmesi (v1.0.0)` | Arquitectura base del tema Stark Tech con CSS personalizado inyectado en GTK4 / Libadwaita. |
| [`0e00f79`](https://github.com/TheLioN25/g502-profile-manager/commit/0e00f79) | `docs: consolidar estado global 100% blindado (28/28 modulos) en diario-mutaciones` | Documentación exhaustiva del análisis de mutaciones completado en todo el proyecto. |
| [`e0f55b2`](https://github.com/TheLioN25/g502-profile-manager/commit/e0f55b2) | `test(storage): blindar import_data, file_lock recursivo y respaldo de corrupcion en JsonProfileRepository (286 tests)` | Blindaje de mutaciones en capa de persistencia atómica tolerante a fallos y bloqueos de archivo. |
| [`d42b4c5`](https://github.com/TheLioN25/g502-profile-manager/commit/d42b4c5) | `test(services): blindar defaults y resolucion desktop en ProfileManager (283 tests)` | Blindaje de mutaciones en resolución de perfiles y defaults de sistema. |
| [`fdae560`](https://github.com/TheLioN25/g502-profile-manager/commit/fdae560) | `test(services): blindar parseo y actualizacion de manifiestos en ActionCatalogService (281 tests)` | Blindaje de mutaciones en catálogos de acciones y manifiestos de juegos. |
| [`0a3124c`](https://github.com/TheLioN25/g502-profile-manager/commit/0a3124c) | `test(i18n): blindar traducciones bilingues con conjunciones logicas (279 tests)` | Blindaje de mutaciones en motor de internacionalización inglés / español. |
| [`f3dc2c1`](https://github.com/TheLioN25/g502-profile-manager/commit/f3dc2c1) | `test(gui): blindar fallback de notificaciones en MainWindow (279 tests)` | Blindaje de mutaciones en fallbacks de notificación y manejo de señales en ventana principal. |
| [`413e0ce`](https://github.com/TheLioN25/g502-profile-manager/commit/413e0ce) | `test(gui): blindar introspeccion XML de StatusNotifierItem en tray (278 tests)` | Blindaje de mutaciones en introspección D-Bus y registro en `org.kde.StatusNotifierWatcher`. |
| [`2bf3b15`](https://github.com/TheLioN25/g502-profile-manager/commit/2bf3b15) | `test(gui): blindar propiedades y parser LED en G502MouseDiagram (277 tests)` | Blindaje de mutaciones en renderizado vectorial Cairo, parsing de colores LED y diagramas interactivos. |
