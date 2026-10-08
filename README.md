# Logitech G502 Family Profile Manager (Linux)

<p align="center">
  <a href="README.md"><b>🇺🇸 English</b></a> | <a href="README.es.md">🇪🇸 Español</a>
</p>

[![CI Pipeline](https://github.com/TheLioN25/g502-profile-manager/actions/workflows/ci.yml/badge.svg)](https://github.com/TheLioN25/g502-profile-manager/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/badge/tests-155%20passed-brightgreen.svg)](#-unit-tests-execution)
[![Python](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](pyproject.toml)

Advanced profile manager and real-time reactive automation engine for **Logitech G502** mice on Linux.

Visually configure buttons, macros, DPI sensitivity stages, and LIGHTSYNC RGB lighting, with seamless automatic hardware profile switching based on the active game or application via [`ratbagctl`](https://github.com/libratbag/libratbag) (`libratbag`).

<p align="center">
  <img src="docs/images/01_main_window.png" alt="Logitech G502 Family Profile Manager - GTK4 Interface" width="850" />
</p>

---

## 📸 Interface & Features Gallery

| Multi-Profile Support per Game (Guild Wars 2) | Profile Management & Default Profile (Warframe) |
| :---: | :---: |
| <img src="docs/images/02_multi_profiles.png" alt="Multi-Profile Support" width="400" /> | <img src="docs/images/03_profile_options.png" alt="Profile Management" width="400" /> |
| *Multiple profiles per game according to your build, character, or role.* | *Mark your favorite profile with ⭐ as default for reactive switching.* |

<p align="center">
  <img src="docs/images/04_action_assignment.png" alt="Action Picker & Key Mapping" width="550" /><br/>
  <em><b>Action Picker:</b> Categorized shortcuts (Combat, Skills, Clipboard, Multimedia) and direct keyboard key mapping.</em>
</p>

---

## 🌟 Key Features

* 🎨 **Modern Graphical Interface (GTK4 + Libadwaita):**
  * Native Linux design with automatic Dark Mode support.
  * **Two-tier application sidebar:**
    * **Top Section (Configured):** Priority quick access to applications with configured profiles (e.g., *Desktop / System*, *Warframe*, *Guild Wars 2*).
    * **Divider & Reactive Search Bar:** Search bar positioned strategically above unconfigured applications.
    * **Bottom Section (Unconfigured):** Catalog of installed games and apps, searchable on the fly to configure new profiles.
  * **HeaderBar Auto-Profile Switch (⚡):** Toggle real-time background process detection directly from the GUI, keeping the interface 100% fluid in a secondary thread while displaying active title and DPI.
  * **🔔 Native System Tray Indicator (StatusNotifierItem / SNI):**
    * Native integration with KDE Plasma and GNOME taskbars over pure session D-Bus (zero legacy GTK 3 `AppIndicator3` conflicts).
    * Dynamic real-time tooltip showing active profile, detected application, DPI, battery level, and auto-profile status.
    * Interactive click to instantly raise and present the main window.
  * **Interactive Vector Mouse Diagram** rendered in real time with Cairo Canvas: displays button bindings, tooltips, and visual synchronization with the configured LED color.
  * Multi-profile management per application: create, duplicate, rename, delete, and set default profiles.
  * Action Picker with thematic categories (*Combat, Weapons, Skills, Movement, Productivity*) and quick custom key binding.
  * Instant hardware application running in background thread with debouncing to prevent interface locks.

* 🌐 **Bilingual Support & Internationalization (EN / ES):**
  * Full native interface, CLI, and system tray support for both **English** and **Spanish**.
  * Interactive language switcher in the HeaderBar with live on-the-fly UI text and diagram reloading without restarts.
  * Automatic regional locale detection on first launch via system environment inspection (`$LC_ALL`, `$LC_MESSAGES`, `$LANG`) and standalone helper script (`scripts/detect-locale.sh`).
  * Dynamic FreeDesktop / XDG desktop entry name localization (`Name[en]` vs `Name[es]`).

* 🖱️ **Logitech G502 Family Multi-Variant Support:**
  * Supported models: **G502 Proteus Core**, **G502 Proteus Spectrum**, **G502 HERO**, **G502 LIGHTSPEED**, **G502 X**, and **G502 X PLUS / Wireless**.
  * Dynamic contextual adaptation: sensor limits (12,000 vs 25,600 DPI), hardware value clamping, lighting zone controls, and wireless battery indicators in both HeaderBar and System Tray.
  * *Community calibration feedback:* G502 HERO is the primary hardware-verified model. For other variants, calibrated support is powered by `libratbag` specifications; if you notice any behavior to fine-tune on your device, report it via [GitHub Issues](https://github.com/TheLioN25/g502-profile-manager/issues) to help refine calibration.

* 🔄 **Reactive Automation Engine (`engine.py`):**
  * Lightweight continuous process monitoring in background (via CLI or GUI switch).
  * **Unified Application Discovery:**
    * 🎮 **Steam:** Detects installed and running games by parsing VDF libraries and `.acf` manifests (`steam:<appid>`).
    * ⚔️ **Epic Games:** Automatic discovery across Linux launchers (Heroic Games Launcher, Legendary, and Lutris).
    * 🖥️ **Linux Desktop:** Integration with standard system `.desktop` files (XDG).
  * **Smart Fallback:** Exiting a game, stopping the engine, or turning off the switch automatically restores the **Desktop / System** profile (`desktop:general`).

* ⚙️ **Native System Service (`systemd --user`):**
  * Configured as a native user daemon with autostart on login, crash restart, and unified control from terminal or GUI switch.

* 🛡️ **Total Hardware Isolation (G-HUB Model) & Anti-Cheat Compliance:**
  * Eliminates unwanted lingering state in the mouse EEPROM.
  * Unassigned buttons in any profile automatically revert to factory defaults (*Back, Forward, DPI Shift, Profile Cycle*), preventing game keys from leaking into the desktop.
  * Strict 1:1 hardware mapping policy with zero automated or timed click loops, keeping accounts safe from anti-cheat bans (EasyAntiCheat, BattlEye, Ricochet, etc.).

* 🧩 **Modular Catalogs & Presets (`presets/`):**
  * Extensible JSON presets for titles like **Warframe**, **Guild Wars 2**, and **AION 2** (including profession F1–F5 keys and custom actions), plus desktop productivity shortcuts.

* 🧪 **Exhaustive Test Suite:**
  * **155 automated unit tests** covering domain logic, atomic storage, hardware adapters, GUI presentation, system tray D-Bus, i18n, desktop packaging, and systemd integration.

---

## 🏗️ Project Architecture

Built with **Domain-Driven Design (DDD)** and **Clean Architecture** principles, enforcing strict decoupling between business logic, hardware drivers, and presentation layers:

> 📘 **Full Architecture Documentation:** For comprehensive C4 diagrams (Context, Containers, Components), layer breakdown, and Architecture Decision Records (ADR-001 through ADR-006), see [**`docs/ARCHITECTURE.md`**](docs/ARCHITECTURE.md).

```text
g502-profile-manager/
├── docs/                        # Architecture and technical documentation
│   └── ARCHITECTURE.md          # C4 diagrams, Clean Architecture, and ADRs
├── data/                        # Desktop assets and system units
│   ├── icons/                   # High-resolution SVG icon (io.github.thelion.G502ProfileManager.svg)
│   ├── io.github.thelion.G502ProfileManager.desktop # Standard XDG desktop entry
│   └── g502-profile-manager.service # systemd --user service unit
├── presets/                     # Modular JSON presets per game/app
│   ├── desktop_general.json
│   ├── steam_1284210_guildwars2.json
│   ├── steam_230410_warframe.json
│   └── steam_3393110_aion2.json
├── scripts/                     # System utility and installation scripts
│   ├── detect-locale.sh         # Regional language detection and configuration
│   ├── install-bin.sh           # Installs g502 and g502-gui launchers in user PATH
│   ├── uninstall-bin.sh         # Clean uninstall of binaries from ~/.local/bin
│   ├── install-desktop.sh       # Installs desktop launcher and SVG icon in system
│   ├── uninstall-desktop.sh     # Removes XDG launcher and icon
│   ├── install-service.sh       # Installs and starts systemd --user service
│   └── uninstall-service.sh     # Stops and removes systemd service
├── src/
│   ├── domain/                  # Pure domain entities (zero external dependencies)
│   │   ├── application.py       # Application entity & Action Value Object
│   │   ├── button.py            # G502 button definitions & invariants
│   │   ├── dpi.py               # DPI configuration and range validation
│   │   └── profile.py           # Profile aggregate root and binding rules
│   ├── services/                # Application services and use cases
│   │   ├── action_catalog.py    # Catalog and preset orchestration
│   │   └── profile_manager.py   # Profile lifecycle and persistence use cases
│   ├── storage/                 # Infrastructure and persistence layer
│   │   └── profile_repository.py# Atomic JSON repository with dynamic reload
│   ├── adapters/                # External hardware and discovery adapters
│   │   ├── ratbag_adapter.py    # libratbag/ratbagctl communication & EEPROM isolation
│   │   └── application_discovery_adapter.py # Unified app discovery (Steam + Epic + Desktop)
│   ├── gui/                     # GTK4 / Libadwaita presentation layer
│   │   ├── app.py               # Application entry point
│   │   ├── window.py            # Main window & reactive event controller
│   │   ├── tray.py              # System Tray indicator (D-Bus StatusNotifierItem)
│   │   ├── dialogs.py           # Modal dialogs (ActionPicker, NewProfile)
│   │   ├── mouse_diagram.py     # Interactive Cairo Canvas mouse diagram
│   │   └── style.css            # Custom Adwaita stylesheet
│   ├── i18n.py                  # Singleton i18n manager and translation catalog
│   ├── engine.py                # Real-time background automation daemon
│   ├── cli.py                   # Command-line interface tool
│   ├── steam_discovery.py       # Steam VDF / ACF library parser
│   ├── epic_discovery.py        # Epic Games launcher discovery (Heroic/Legendary)
│   ├── desktop_entries.py       # Linux .desktop parser with XDG localization
│   └── process_discovery.py     # System process inspection
└── tests/                       # Suite of 155 automated unit tests
```

---

## 🧭 Code & Architecture Review Guide

For reviewers evaluating code quality, design patterns, and architecture:

| Technical Area | Component / Path | Key Aspects to Evaluate |
| :--- | :--- | :--- |
| **Global Architecture & C4** | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Mermaid C4 diagrams (Context, Containers, Components) and Clean Architecture boundaries. |
| **Design Decisions (ADRs)** | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md#5-registros-de-decisiones-de-arquitectura-adr) | 6 formal ADRs (Anti-Cheat 1:1, pure D-Bus SNI, atomic storage, systemd, etc.). |
| **Pure Domain Layer (DDD)** | [`src/domain/`](src/domain/) | Uncoupled entities and value objects (`Profile`, `Button`, `Action`, `DpiConfiguration`). |
| **Internationalization (i18n)** | [`src/i18n.py`](src/i18n.py) | Decoupled `I18nManager` singleton, atomic storage in `~/.config/g502-preferences.json`, regional detection. |
| **Atomic Persistence** | [`src/storage/profile_repository.py`](src/storage/profile_repository.py) | Two-phase atomic write (`NamedTemporaryFile` + `replace`) and `mtime` concurrent sync. |
| **Hardware Isolation** | [`src/adapters/ratbag_adapter.py`](src/adapters/ratbag_adapter.py) | Mouse EEPROM memory sanitization and factory defaults restoration (G-HUB model). |
| **D-Bus System Tray** | [`src/gui/tray.py`](src/gui/tray.py) | StatusNotifierItem over pure `Gio.DBusConnection` (eliminating GTK3/GTK4 runtime collisions). |
| **GUI Concurrency** | [`src/gui/window.py`](src/gui/window.py) | Non-blocking background monitoring (`threading.Thread`) and safe GTK dispatch via `GLib.idle_add`. |
| **Unit Test Suite**| [`tests/`](tests/) | 155 unit tests with pure test doubles (`python3 -m unittest discover -s tests`). |
| **CI/CD Pipeline** | [`.github/workflows/ci.yml`](.github/workflows/ci.yml) | Multi-version Python automation with headless display server validation (`xvfb-run`). |

---

## 📦 Installation

### Option A: Arch Linux / Manjaro / CachyOS / EndeavourOS (Native)
Install via `makepkg` (or your preferred AUR helper like `yay`):
```bash
git clone https://github.com/TheLioN25/g502-profile-manager.git
cd g502-profile-manager/packaging/aur
makepkg -si
```
*(Registers the package in `pacman` and automatically installs `g502` and `g502-gui` commands, desktop launcher with high-resolution SVG icon, presets, and `systemd` user service).*

### Option B: Quick System Install (Any Linux Distribution)
```bash
git clone https://github.com/TheLioN25/g502-profile-manager.git
cd g502-profile-manager

# 1. Install "g502" and "g502-gui" launchers in ~/.local/bin (auto-detects language):
./scripts/install-bin.sh

# 2. Register desktop launcher and icon in app menu (KDE/GNOME):
./scripts/install-desktop.sh

# 3. (Optional) Enable reactive background daemon with systemd --user:
./scripts/install-service.sh
```

---

## 📋 System Requirements

1. **Linux** with Python 3.10 or higher.
2. **libratbag / ratbagctl:** Mouse configuration daemon for Linux.
3. **GUI Libraries:** GTK4, Libadwaita, and PyGObject.

### Dependency Installation

* **Debian / Ubuntu / Pop!_OS:**
  ```bash
  sudo apt install libratbag-tools ratbagd python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 python3-cairo
  ```

* **Arch Linux / Manjaro / CachyOS:**
  ```bash
  sudo pacman -S libratbag python-gobject gtk4 libadwaita python-cairo
  ```

* **Fedora:**
  ```bash
  sudo dnf install libratbag-ratbagd python3-gobject gtk4 libadwaita python3-cairo
  ```

### Enable Mouse Service
Ensure the `ratbagd` daemon is running and your G502 is detected:
```bash
sudo systemctl enable --now ratbagd
ratbagctl list
```

---

## 🚀 Usage Guide

### 1. Graphical Interface (Recommended)
Launch the visual manager with interactive mouse diagram:
```bash
python3 src/gui/app.py
```
* **Language Switcher:** Switch between 🇺🇸 English and 🇪🇸 Español on the fly from the HeaderBar menu.
* **Application Organizer:** Browse configured titles in the top section or use the search bar to configure new profiles from the bottom catalog.
* **Auto-Profile Switch (⚡):** Toggle background monitoring to automatically switch hardware profiles when entering or exiting games without freezing the window.
* **Full Customization:** Adjust DPI stages, LED lighting color/effects, or click any button on the mouse canvas to bind a catalog action or custom key.
* **Apply to Mouse:** Instantly write configurations into the mouse physical on-board memory.

### 2. Desktop Launcher Integration (KDE Plasma / GNOME)
Register the application in your Linux application menu (Kickoff, KRunner, taskbar) with its native SVG icon:
```bash
# Install launcher in ~/.local/share/applications/ and icon in ~/.local/share/icons/
./scripts/install-desktop.sh

# To uninstall launcher:
./scripts/uninstall-desktop.sh
```

### 3. Background User Service (`systemd --user`)
To run reactive auto-detection silently on user session login:
```bash
# Install and start user systemd service
./scripts/install-service.sh

# Check service status:
python3 src/cli.py service-status

# View live logs via journalctl:
journalctl --user -u g502-profile-manager.service -f

# Stop and uninstall service:
./scripts/uninstall-service.sh
```

### 4. Background Automation Engine (CLI Daemon Mode)
Run process auto-detection directly from a terminal or script:
```bash
python3 src/engine.py
```

### 5. Command-Line Interface (CLI) & Binaries in PATH
Use the CLI via `python3 src/cli.py` or install terminal shortcuts (`~/.local/bin`):
```bash
# Run commands directly:
g502 list                       # List detected applications
g502 profiles                   # List configured profiles
g502 status                     # Hardware diagnostics, variant, and battery level
g502 export backup.json         # Export profiles to JSON
g502 --lang es status           # Run CLI in Spanish
g502-gui                        # Open graphical user interface
```

### 6. Profile Portability & Backup (`export` / `import`)
Share profiles between machines or create configuration backups:
```bash
# Export all profiles to a JSON file:
g502 export my_backup.json

# Export profiles for a specific application:
g502 export warframe_profiles.json --app steam:230410

# Import profiles from file (safely skips duplicates):
g502 import my_backup.json

# Import overwriting existing profiles with matching IDs:
g502 import my_backup.json --overwrite
```

---

## 🎮 Game Compatibility (Steam / Proton / Wayland)

When playing Windows games on Linux through **Steam Play / Proton**:
* Use stable Proton versions such as **Proton 10** or **Proton Experimental**.
* If running under Wayland (e.g., KDE Plasma or GNOME) and mouse key bindings fail to register in-game, add this launch option in Steam game properties:
  ```bash
  PROTON_ENABLE_WAYLAND=0 %command%
  ```
  *(Or with MangoHud: `PROTON_ENABLE_WAYLAND=0 mangohud %command%`)*. This ensures keyboard signals travel reliably through the XWayland translation layer.

---

## 🧪 Unit Tests Execution

To run the complete suite of 155 automated tests:
```bash
python3 -m unittest discover -s tests -v
```
Tests validate domain invariants, atomic disk persistence, profile import/export, hardware communication via test doubles, internationalization, and GUI logic without requiring connected physical hardware.

---

## 📄 License

Project licensed under the MIT License. See [LICENSE](LICENSE) or [pyproject.toml](pyproject.toml) for details.
