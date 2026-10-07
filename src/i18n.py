"""
Módulo central de Internacionalización (i18n) para G502 Profile Manager.

Provee traducción estándar mediante _(texto), persistencia atómica
de las preferencias del usuario (~/.config/g502-preferences.json) y
soporte bilingüe completo (Español / Inglés).
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Callable

logger = logging.getLogger("g502.i18n")

AVAILABLE_LANGUAGES: dict[str, str] = {
    "es": "Español",
    "en": "English",
}

DEFAULT_LANGUAGE: str = "es"
DEFAULT_PREFERENCES_FILE: Path = Path.home() / ".config/g502-preferences.json"

# Catálogo completo de traducciones al Inglés (Español es el idioma base)
TRANSLATIONS_EN: dict[str, str] = {
    # Ventana Principal y HeaderBar
    "G502 Profile Manager": "G502 Profile Manager",
    "Selecciona una aplicación": "Select an application",
    "Buscando mouse...": "Searching for mouse...",
    "Auto-Perfil": "Auto-Profile",
    "Conmutación automática de perfiles según el juego o aplicación activa": "Automatic profile switching based on active game or application",
    "Aplicar al Ratón": "Apply to Mouse",
    "Escribir perfil directamente al G502 HERO": "Write profile directly to mouse hardware",
    "Guardar": "Save",
    "Guardar cambios del perfil": "Save profile changes",
    "Mis Juegos y Apps": "My Games & Apps",
    "Instalados en el sistema": "Installed on system",
    "Refrescar biblioteca": "Refresh library",
    "Seleccionar perfil para este juego": "Select profile for this game",
    "Crear nuevo perfil": "Create new profile",
    "Opciones del perfil": "Profile options",
    "⭐ Marcar como Predeterminado": "⭐ Set as Default",
    "📋 Duplicar Perfil": "📋 Duplicate Profile",
    "🗑️ Eliminar Perfil": "🗑️ Delete Profile",

    # Pestañas / Stack
    "Botones": "Buttons",
    "Rendimiento (DPI)": "Performance (DPI)",
    "Esquema Interactivo G502 HERO": "Interactive G502 HERO Diagram",
    "Haz clic en cualquier botón del ratón para asignar una acción": "Click any mouse button to assign an action",
    "Sin asignar": "Unassigned",
    # Hardware & Estado
    "Conectado": "Connected",
    "Desconectado": "Disconnected",
    "○ Ratón Desconectado": "○ Mouse Disconnected",
    "○ ratbagd no disponible": "○ ratbagd not available",

    # Sidebar y Búsqueda
    "Configurado": "Configured",
    "Buscar juego o app...": "Search game or app...",

    # Columna de botones y chips
    "Sin acción asignada": "No action assigned",
    "Cambiar": "Change",
    "Colores Calibrados G502:": "Calibrated G502 Colors:",
    "Velocidad del Efecto": "Effect Speed",
    "Duración de cada pulsación o ciclo de color": "Duration of each pulse or color cycle",
    "1s (Rápido)": "1s (Fast)",
    "2s (Normal)": "2s (Normal)",
    "3s (Suave)": "3s (Smooth)",
    "5s (Lento)": "5s (Slow)",
    "10s (Relax)": "10s (Relax)",

    # Submenú Modal de Asignación (Categorías de Presets)
    "Portapapeles": "Clipboard",
    "Navegación": "Navigation",
    "Multimedia": "Multimedia",
    "Combate": "Combat",
    "Armas": "Weapons",
    "Habilidades": "Abilities",
    "Profesión": "Profession",
    "Apoyo y Élite": "Support & Elite",
    "Movimiento": "Movement",
    "Interacción": "Interaction",
    "Edición": "Editing",
    "General": "General",
    "Comando:": "Command:",

    # Acciones de escritorio (Presets)
    "Copiar": "Copy",
    "Copiar selección al portapapeles (Ctrl+C)": "Copy selection to clipboard (Ctrl+C)",
    "Pegar": "Paste",
    "Pegar contenido del portapapeles (Ctrl+V)": "Paste clipboard content (Ctrl+V)",
    "Cortar": "Cut",
    "Cortar selección al portapapeles (Ctrl+X)": "Cut selection to clipboard (Ctrl+X)",
    "Deshacer": "Undo",
    "Deshacer última acción (Ctrl+Z)": "Undo last action (Ctrl+Z)",
    "Rehacer": "Redo",
    "Rehacer última acción deshecha (Ctrl+Y)": "Redo last undone action (Ctrl+Y)",
    "Pestaña Siguiente": "Next Tab",
    "Avanzar a la siguiente pestaña en navegador o IDE (Ctrl+Tab)": "Advance to next tab in browser or IDE (Ctrl+Tab)",
    "Pestaña Anterior": "Previous Tab",
    "Retroceder a la pestaña anterior (Ctrl+Shift+Tab)": "Go back to previous tab (Ctrl+Shift+Tab)",
    "Cerrar Pestaña": "Close Tab",
    "Cerrar la pestaña activa (Ctrl+W)": "Close active tab (Ctrl+W)",
    "Silenciar Audio": "Mute Audio",
    "Alternar silencio del volumen maestro": "Toggle master volume mute",
    "Reproducir / Pausar": "Play / Pause",
    "Alternar reproducción de música o video": "Toggle music or video playback",

    # Acciones comunes de juegos (Warframe, GW2, AION 2)
    "Habilidad 1": "Ability 1",
    "Habilidad 2": "Ability 2",
    "Habilidad 3": "Ability 3",
    "Habilidad 4 (Ultimate)": "Ability 4 (Ultimate)",
    "Transferencia / Operador": "Transference / Operator",
    "Arma Primaria": "Primary Weapon",
    "Arma Secundaria": "Secondary Weapon",
    "Cuerpo a Cuerpo": "Melee",
    "Ataque Pesado / Disparo Alt": "Heavy Attack / Alt Fire",
    "Marcar Punto de Ruta": "Waypoint / Tag",

    "Estado": "Status",
    "Hardware": "Hardware",
    "Sensor máx": "Max Sensor",
    "Sin RGB": "No RGB",
    "zona(s)": "zone(s)",
    "Iluminación": "Lighting",
    "Soporte": "Support",
    "Experimental (reporta anomalías en:": "Experimental (report anomalies at:",
    "Ningún ratón G502 detectado vía libratbag.": "No G502 mouse detected via libratbag.",
    "Repositorio": "Repository",
    "perfil(es) registrado(s)": "registered profile(s)",

    "Laterales": "Side Buttons",
    "Superiores": "Top Buttons",
    "Rueda de Desplazamiento": "Scroll Wheel",
    "Clics Principales": "Primary Clicks",
    "Cambiar": "Change",
    "Botón G5 (Lateral Delantero)": "Button G5 (Front Side)",
    "Botón G4 (Lateral Trasero)": "Button G4 (Rear Side)",
    "Botón SNIPER (Pulgar / DPI Shift)": "SNIPER Button (Thumb / DPI Shift)",
    "Botón G7 (DPI Down)": "Button G7 (DPI Down)",
    "Botón G8 (DPI Up)": "Button G8 (DPI Up)",
    "Botón G9 (Cambio de Perfil / Superior)": "Button G9 (Profile Switch / Top)",
    "Clic Central (Rueda)": "Middle Click (Wheel)",
    "Inclinación Rueda Izquierda": "Wheel Tilt Left",
    "Inclinación Rueda Derecha": "Wheel Tilt Right",

    "Quitar Asignación": "Remove Assignment",
    "Catálogo de": "Catalog for",
    "Buscar acción o habilidad...": "Search action or ability...",
    "Asigna directamente cualquier tecla del teclado": "Directly assign any keyboard key",
    "Ingresa un nombre descriptivo para esta configuración.": "Enter a descriptive name for this configuration.",
    "Alternativo": "Alternative",
    "Asignar": "Assign",

    "Asignación Personalizada": "Custom Assignment",
    "Tecla o atajo": "Key or shortcut",
    "Restablecer a Valor de Fábrica": "Reset to Factory Default",
    "Crear Nuevo Perfil": "Create New Profile",
    "Detalles del Perfil": "Profile Details",
    "Nombre del Perfil": "Profile Name",
    "Idioma / Language": "Language / Idioma",
    "Cambiar idioma": "Change language",

    # Sección DPI
    "Sensibilidad DPI": "DPI Sensitivity",
    "Nivel DPI Activo": "Active DPI Level",
    "DPI Sniper / Cambio": "Sniper / Shift DPI",
    "DPI alternativo al presionar el botón Sniper": "Alternative DPI when pressing the Sniper button",

    # Sección Iluminación LED
    "Iluminación LED": "LED Lighting",
    "Color Primario": "Primary Color",
    "Color del logotipo y franjas luminosas": "Logo and lighting strip color",
    "Modo": "Mode",
    "Estático": "Static",
    "Respiración": "Breathing",
    "Ciclo de Color": "Color Cycle",
    "Apagado": "Off",

    # Sección Asignación de Botones
    "Asignación de Botones": "Button Mapping",
    "Haz clic en cualquier botón del diagrama para asignarle una tecla o macro": "Click any button on the diagram to assign a key or macro",

    # Banner Comunitario y Diálogo de Feedback
    "Soporte experimental: Ayúdanos a calibrar este modelo reportando cualquier anomalía.": "Experimental support: Help us calibrate this model by reporting any anomalies.",
    "Dar Feedback / Reportar": "Give Feedback / Report",
    "Sensibilidad del Sensor HERO 25K": "HERO 25K Sensor Sensitivity",
    "Ajusta los puntos por pulgada (DPI) para una puntería precisa": "Adjust dots per inch (DPI) for precise aiming",
    "Sensibilidad Principal": "Primary Sensitivity",
    "Sensibilidad del Botón Sniper (DPI Shift)": "Sniper Button Sensitivity (DPI Shift)",
    "Sensibilidad temporal activada al mantener presionado el botón pulgar": "Temporary sensitivity activated while holding the thumb button",
    "DPI de Francotirador": "Sniper DPI",
    "Iluminación LIGHTSYNC RGB": "LIGHTSYNC RGB Lighting",
    "Personaliza el modo, color y efectos del logotipo G e indicador DPI": "Customize the mode, color, and effects of the G logo and DPI indicator",
    "Efecto de Iluminación": "Lighting Effect",
    "Color de Iluminación": "Lighting Color",
    "Haz clic en la muestra para abrir la paleta o introduce el código hexadecimal": "Click the sample to open the palette or enter the hex code",
    "Respiración (Pulsación)": "Breathing (Pulse)",
    "Ciclo de Espectro (Arcoíris)": "Spectrum Cycle (Rainbow)",
    "Ayúdanos a Mejorar y Calibrar tu Ratón": "Help Us Improve and Calibrate Your Mouse",
    "💬 Abrir en Reddit": "💬 Open in Reddit",
    "🐙 GitHub Issues": "🐙 GitHub Issues",
    "• Reddit: Ideal para comentar rápido en la comunidad sin necesidad de conocimientos de desarrollo.": "• Reddit: Great for quick community feedback without developer knowledge.",
    "• GitHub: Recomendado para reportes técnicos detallados y seguimiento de bugs.": "• GitHub: Recommended for detailed technical reports and bug tracking.",

    "Feedback y Reportes de Compatibilidad": "Feedback & Compatibility Reports",
    "¿Dónde prefieres compartir tus observaciones?": "Where would you like to share your feedback?",
    "Reddit (Hilo Oficial)": "Reddit (Official Thread)",
    "GitHub (Abrir Issue)": "GitHub (Open Issue)",
    "Comunidad Reddit sobre G502": "G502 Reddit Community",
    "Seguimiento técnico y bugs": "Technical tracking and bugs",

    # Diálogos Modales (Crear, Eliminar)
    "Nuevo Perfil": "New Profile",
    "Nombre del Perfil:": "Profile Name:",
    "Crear": "Create",
    "Cancelar": "Cancel",
    "Aceptar": "OK",
    "Eliminar": "Delete",
    "¿Estás seguro de que deseas eliminar este perfil?": "Are you sure you want to delete this profile?",
    "Esta acción no se puede deshacer.": "This action cannot be undone.",

    # Selector de Acciones
    "Asignar Botón": "Assign Button",
    "Acciones Recomendadas": "Recommended Actions",
    "Tecla Personalizada": "Custom Key",
    "Restablecer Valor de Fábrica": "Reset to Factory Default",
    "Presiona una tecla...": "Press a key...",
    "Buscar acciones...": "Search actions...",
    "Sin categoría": "Uncategorized",

    # Diagrama del Ratón (Nombres de Botones y Tooltips)
    "Click Izquierdo": "Left Click",
    "Click Derecho": "Right Click",
    "Click Central": "Middle Click",
    "Botón G4 (Atrás)": "Button G4 (Back)",
    "Botón G5 (Adelante)": "Button G5 (Forward)",
    "Botón Sniper": "Sniper Button",
    "Botón G7": "Button G7",
    "Botón G8": "Button G8",
    "Botón G9": "Button G9",
    "Rueda Izquierda": "Wheel Left",
    "Rueda Derecha": "Wheel Right",
    "Sin asignar (predeterminado)": "Unassigned (default)",

    # Notificaciones Toast
    "Perfil guardado exitosamente.": "Profile saved successfully.",
    "Perfil aplicado al ratón con éxito.": "Profile applied to mouse successfully.",
    "Perfil duplicado exitosamente.": "Profile duplicated successfully.",
    "Perfil eliminado exitosamente.": "Profile deleted successfully.",
    "Perfil establecido como predeterminado.": "Profile set as default.",
    "Error al aplicar perfil al ratón.": "Error applying profile to mouse.",
    "Idioma cambiado exitosamente.": "Language changed successfully.",

    # Bandeja del Sistema (Tray / SNI)
    "Auto: Activo": "Auto: Active",
    "Auto: Inactivo": "Auto: Inactive",
    "Escritorio / Sistema": "Desktop / System",
    "Escritorio": "Desktop",
    "Batería": "Battery",
    "Abrir Administrador": "Open Manager",
    "Activar / Desactivar Auto-Perfil": "Toggle Auto-Profile",
    "Salir": "Quit",

    # Interfaz CLI
    "Descubriendo aplicaciones instaladas...": "Discovering installed applications...",
    "Total aplicaciones detectadas:": "Total applications detected:",
    "Presets disponibles": "Presets available",
    "No hay perfiles configurados.": "No profiles configured.",
    "Perfiles configurados": "Configured profiles",
    "PREDETERMINADO": "DEFAULT",
    "Perfil creado exitosamente.": "Profile created successfully.",
    "Catálogo disponible:": "Catalog available:",
    "acciones en": "actions in",
    "categorías.": "categories.",
    "Estado del Sistema y Hardware Logitech G502": "Logitech G502 Hardware and System Status",
    "Dispositivo Conectado:": "Connected Device:",
    "Variante Detectada:": "Detected Variant:",
    "Nivel de Batería:": "Battery Level:",
    "Inalámbrico": "Wireless",
    "Cableado": "Wired",
    "Motor de Automatización:": "Automation Engine:",
    "Activo": "Active",
    "Inactivo": "Inactive",
    "No se detectó ningún ratón compatible.": "No compatible mouse detected.",
    # LED Lighting y Presets de Velocidad
    "Colores Calibrados G502:": "Calibrated G502 Colors:",
    "Selector de color interactivo": "Interactive color picker",
    "1s (Rápido)": "1s (Fast)",
    "2s (Normal)": "2s (Normal)",
    "3s (Suave)": "3s (Smooth)",
    "5s (Lento)": "5s (Slow)",
    "10s (Relax)": "10s (Relax)",
    "Personaliza el modo, color y efectos del logotipo G e indicadores DPI ({zones} zonas)": "Customize mode, color and effects of the G logo and DPI indicators ({zones} zones)",
    "Iluminación no disponible en {short_name} (modelo sin iluminación RGB)": "Lighting not available on {short_name} (model without RGB lighting)",
    "Iluminación monocromo azul (1 zona) en {short_name}": "Monochrome blue lighting (1 zone) on {short_name}",

    # Soporte Experimental y Banner Comunitario
    "Soporte experimental: Ayúdanos a calibrar este modelo reportando cualquier anomalía.": "Experimental support: Help us calibrate this model by reporting any anomalies.",
    "Soporte experimental para {short_name}: Ayúdanos a calibrarlo reportando cualquier anomalía.": "Experimental support for {short_name}: Help us calibrate it by reporting any issues.",
    "Ayúdanos a Mejorar y Calibrar tu Ratón": "Help Us Improve and Calibrate Your Mouse",
    "Has conectado un {variant_name}. El soporte para este modelo se basa en especificaciones de libratbag y tu experiencia real es clave para seguir perfeccionándolo.\n\n¿Dónde te gustaría compartir tu opinión o reportar alguna anomalía?\n\n• Reddit: Ideal para comentar rápido en la comunidad sin necesidad de conocimientos de desarrollo.\n• GitHub: Recomendado para reportes técnicos detallados y seguimiento de bugs.": "You have connected a {variant_name}. Support for this model is based on libratbag specifications and your real-world experience is key to perfecting it.\n\nWhere would you like to share your feedback or report an issue?\n\n• Reddit: Ideal for quick community discussion without development background.\n• GitHub: Recommended for detailed technical reports and bug tracking.",

    # Diálogos y Botones
    "ej: e, 1, space, leftctrl": "e.g.: e, 1, space, leftctrl",
    "Tecla": "Key",
    "Tecla asignada manualmente": "Manually assigned key",
    "Personalizado": "Custom",
    "Comando:": "Command:",

    # Notificaciones Toast y Avisos de Hardware
    "Biblioteca de aplicaciones sincronizada": "Application library synchronized",
    "Asignado '{action}' al {button}": "Assigned '{action}' to {button}",
    "Quitada asignación de {button}": "Removed assignment from {button}",
    "Perfil activo: {name}": "Active profile: {name}",
    "Perfil '{name}' creado.": "Profile '{name}' created.",
    "'{name}' marcado como predeterminado ⭐": "'{name}' marked as default ⭐",
    "Perfil duplicado: '{name}'": "Duplicated profile: '{name}'",
    "No puedes eliminar el único perfil de este juego.": "You cannot delete the only profile for this game.",
    "Perfil '{name}' eliminado.": "Profile '{name}' deleted.",
    "Perfil '{name}' guardado.": "Profile '{name}' saved.",
    "¡Perfil aplicado con éxito al ratón!": "Profile applied successfully to mouse!",
    "Error: No se detectó ningún ratón de la familia G502 conectado.": "Error: No G502 family mouse detected.",
    "Advertencia: No se pudo aplicar completamente al ratón {variant_name}.": "Warning: Could not completely apply to mouse {variant_name}.",
    "¡Perfil aplicado con éxito al ratón {variant_name}!": "Profile successfully applied to mouse {variant_name}!",
    "Error al comunicar con ratbagctl: {error}": "Error communicating with ratbagctl: {error}",
    "Aplicando...": "Applying...",
    "Aplicar al Ratón": "Apply to Mouse",
    "⚡ Auto-detección activada: supervisando procesos...": "⚡ Auto-detection enabled: monitoring processes...",
    "Auto-detección desactivada: modo escritorio restaurado.": "Auto-detection disabled: desktop mode restored.",
    "Perfil": "Profile",
    "Juego": "Game",
    "Sistema": "System",
}


def detect_system_language() -> str:
    """
    Detecta automáticamente el idioma preferido según la configuración regional del sistema.
    Si el entorno (LC_ALL, LC_MESSAGES, LANG, LANGUAGE) inicia con 'es', devuelve 'es'.
    De lo contrario, devuelve 'en'.
    """
    for var_name in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        val = os.environ.get(var_name, "").strip().lower()
        if val:
            if val.startswith("es"):
                return "es"
            return "en"

    try:
        import locale
        loc = locale.getdefaultlocale()[0]
        if loc and loc.strip().lower().startswith("es"):
            return "es"
    except Exception:
        pass

    return "en"


class I18nManager:
    """
    Gestor singleton de internacionalización.
    Controla el idioma activo, la persistencia en disco y los despachos reactivos.
    """

    def __init__(self, preferences_file: Path | str | None = None):
        if preferences_file is None:
            self._preferences_file = DEFAULT_PREFERENCES_FILE
        else:
            self._preferences_file = Path(preferences_file).expanduser().resolve()

        self._current_language: str = DEFAULT_LANGUAGE
        self._callbacks: list[Callable[[str], None]] = []
        self._load_preferences()

    @property
    def preferences_file(self) -> Path:
        return self._preferences_file

    def set_preferences_file(self, path: Path | str) -> None:
        """Modifica la ruta de almacenamiento (útil para tests unitarios aislados)."""
        self._preferences_file = Path(path).expanduser().resolve()
        self._load_preferences()

    def get_language(self) -> str:
        """Devuelve el código del idioma activo ('es' o 'en')."""
        return self._current_language

    def set_language(self, lang_code: str, persist: bool = True) -> None:
        """
        Establece el idioma activo, guarda en disco si persist=True
        y notifica a los observadores registrados.
        """
        code = lang_code.strip().lower()
        if code not in AVAILABLE_LANGUAGES:
            logger.warning("Idioma '%s' no soportado. Usando fallback '%s'.", lang_code, DEFAULT_LANGUAGE)
            code = DEFAULT_LANGUAGE

        if self._current_language == code and not persist:
            return

        self._current_language = code
        if persist:
            self._save_preferences()

        for cb in list(self._callbacks):
            try:
                cb(self._current_language)
            except Exception as e:
                logger.error("Error en callback de cambio de idioma: %s", e)

    def register_callback(self, callback: Callable[[str], None]) -> None:
        """Registra un observador que se invocará cuando cambie el idioma."""
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def unregister_callback(self, callback: Callable[[str], None]) -> None:
        """Elimina un observador registrado."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def translate(self, text: str) -> str:
        """
        Traduce el texto dado al idioma activo.
        Si está en 'es' o la clave no existe en el catálogo, retorna el texto original.
        """
        if not text or self._current_language == "es":
            return text

        return TRANSLATIONS_EN.get(text, text)

    def _load_preferences(self) -> None:
        """Carga la preferencia de idioma desde el archivo JSON de configuración."""
        if not self._preferences_file.exists():
            self._current_language = detect_system_language()
            try:
                self._save_preferences()
            except Exception:
                pass
            return

        try:
            with open(self._preferences_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                lang = data.get("language", DEFAULT_LANGUAGE)
                if isinstance(lang, str) and lang.strip().lower() in AVAILABLE_LANGUAGES:
                    self._current_language = lang.strip().lower()
                else:
                    self._current_language = DEFAULT_LANGUAGE
            else:
                self._current_language = DEFAULT_LANGUAGE
        except Exception as e:
            logger.warning("No se pudo leer preferencias de idioma desde %s: %s", self._preferences_file, e)

    def _save_preferences(self) -> None:
        """Guarda la preferencia de idioma en disco de forma atómica."""
        try:
            self._preferences_file.parent.mkdir(parents=True, exist_ok=True)
            tmp_file = self._preferences_file.with_suffix(f".tmp.{os.getpid()}")

            data = {}
            if self._preferences_file.exists():
                try:
                    with open(self._preferences_file, "r", encoding="utf-8") as f:
                        loaded = json.load(f)
                        if isinstance(loaded, dict):
                            data = loaded
                except Exception:
                    data = {}

            data["language"] = self._current_language

            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

            tmp_file.replace(self._preferences_file)
        except Exception as e:
            logger.error("Error al guardar preferencias de idioma en %s: %s", self._preferences_file, e)


# Instancia singleton global
_manager = I18nManager()


def gettext(text: str) -> str:
    """Función canónica de traducción."""
    return _manager.translate(text)


def _(text: str) -> str:
    """Alias estándar gettext para internacionalización."""
    return _manager.translate(text)


def get_language() -> str:
    """Retorna el idioma actual ('es' o 'en')."""
    return _manager.get_language()


def set_language(lang_code: str, persist: bool = True) -> None:
    """Establece el idioma activo ('es' o 'en')."""
    _manager.set_language(lang_code, persist=persist)


def get_available_languages() -> dict[str, str]:
    """Retorna los idiomas disponibles {'es': 'Español', 'en': 'English'}."""
    return dict(AVAILABLE_LANGUAGES)


def register_language_change_callback(callback: Callable[[str], None]) -> None:
    """Registra una función a ejecutar cuando el idioma cambie."""
    _manager.register_callback(callback)


def unregister_language_change_callback(callback: Callable[[str], None]) -> None:
    """Elimina la función registrada."""
    _manager.unregister_callback(callback)


def set_preferences_file(path: Path | str) -> None:
    """Configura el archivo de preferencias (usado en tests unitarios)."""
    _manager.set_preferences_file(path)


def reload_preferences() -> None:
    """Recarga las preferencias de disco."""
    _manager._load_preferences()


def detect_language() -> str:
    """Retorna el idioma detectado automáticamente del entorno del sistema."""
    return detect_system_language()
