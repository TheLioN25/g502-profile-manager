#!/usr/bin/env bash
# ==============================================================================
# detect-locale.sh — Detección Automática de Región/Idioma para G502 Profile Manager
# ==============================================================================
# Analiza la configuración regional del sistema operativo y configura
# el idioma inicial ('es' o 'en') en ~/.config/g502-preferences.json.
# ==============================================================================

set -e

CONFIG_FILE="${HOME}/.config/g502-preferences.json"
MODE="auto"
TARGET_LANG=""

# Colores para salida de terminal
GREEN="\033[1;32m"
CYAN="\033[1;36m"
YELLOW="\033[1;33m"
BLUE="\033[1;34m"
BOLD="\033[1m"
RESET="\033[0m"

# Parsear argumentos
while [[ $# -gt 0 ]]; do
    case "$1" in
        --check)
            MODE="check"
            shift
            ;;
        --apply)
            MODE="apply"
            shift
            ;;
        --interactive|-i)
            MODE="interactive"
            shift
            ;;
        --set)
            MODE="set"
            TARGET_LANG="$2"
            shift 2
            ;;
        --help|-h)
            echo "Uso: $0 [OPCIÓN]"
            echo ""
            echo "Opciones:"
            echo "  --check          Inspecciona y muestra la región e idioma detectados sin modificar archivos."
            echo "  --apply          Aplica automáticamente el idioma detectado a la configuración."
            echo "  --interactive    Muestra un menú interactivo en terminal para elegir el idioma."
            echo "  --set <es|en>    Establece directamente el idioma especificado."
            echo "  --help, -h       Muestra esta ayuda."
            echo ""
            exit 0
            ;;
        *)
            echo "Opción desconocida: $1 (usa --help para ver las opciones disponibles)"
            exit 1
            ;;
    esac
done

# 1. Detectar variables del entorno del sistema
SYS_LOCALE="${LC_ALL:-${LC_MESSAGES:-${LANG:-${LANGUAGE:-unknown}}}}"
SYS_LOCALE_CLEAN="$(echo "${SYS_LOCALE}" | tr '[:upper:]' '[:lower:]')"

DETECTED_LANG="en"
REGION_DESC="International / Non-Spanish (English)"

if [[ "${SYS_LOCALE_CLEAN}" == es* ]]; then
    DETECTED_LANG="es"
    REGION_DESC="Comunidad Hispanohablante (Español)"
fi

# 2. Leer preferencia actual si existe
CURRENT_PREF="ninguna (primera ejecución)"
if [[ -f "${CONFIG_FILE}" ]]; then
    CURRENT_PREF="$(python3 -c "
import json
try:
    with open('${CONFIG_FILE}', 'r') as f:
        print(json.load(f).get('language', 'desconocido'))
except Exception:
    print('error_lectura')
" 2>/dev/null || echo "desconocido")"
fi

# 3. Mostrar resumen de diagnóstico
echo -e "${BOLD}======================================================${RESET}"
echo -e "${CYAN}🖱️  G502 Profile Manager — Detección Regional de Idioma${RESET}"
echo -e "${BOLD}======================================================${RESET}"
echo -e "• Variable de sistema (\$LANG / \$LC_*): ${BOLD}${SYS_LOCALE}${RESET}"
echo -e "• Región / Perfil detectado:          ${BOLD}${REGION_DESC}${RESET}"
echo -e "• Idioma sugerido para la app:        ${GREEN}${DETECTED_LANG}${RESET}"
echo -e "• Preferencia actual en disco:        ${YELLOW}${CURRENT_PREF}${RESET}"
echo -e "${BOLD}------------------------------------------------------${RESET}"

# Función para persistir de forma atómica en JSON
save_preference() {
    local lang_to_save="$1"
    python3 -c "
import json, os
from pathlib import Path

pref_file = Path('${CONFIG_FILE}').expanduser()
pref_file.parent.mkdir(parents=True, exist_ok=True)

data = {}
if pref_file.exists():
    try:
        with open(pref_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        data = {}

data['language'] = '${lang_to_save}'

tmp_file = pref_file.with_suffix(f'.tmp.{os.getpid()}')
with open(tmp_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=4, ensure_ascii=False)
tmp_file.replace(pref_file)
"
    echo -e "${GREEN}✓ Preferencia guardada exitosamente:${RESET} language = '${lang_to_save}' en ${CONFIG_FILE}"
}

# 4. Procesar según modo
case "${MODE}" in
    check)
        echo "Modo diagnóstico: No se aplicaron cambios."
        ;;
    set)
        if [[ "${TARGET_LANG}" != "es" && "${TARGET_LANG}" != "en" ]]; then
            echo "Error: Idioma inválido '${TARGET_LANG}'. Usa 'es' o 'en'."
            exit 1
        fi
        save_preference "${TARGET_LANG}"
        ;;
    interactive)
        echo -e "${BOLD}Selecciona el idioma para la interfaz:${RESET}"
        echo "  1) 🇪🇸 Español (Spanish)"
        echo "  2) 🇺🇸 English (Inglés)"
        read -r -p "Opción [1-2, Enter para auto (${DETECTED_LANG})]: " choice
        case "${choice}" in
            1) save_preference "es" ;;
            2) save_preference "en" ;;
            *) save_preference "${DETECTED_LANG}" ;;
        esac
        ;;
    auto|apply)
        save_preference "${DETECTED_LANG}"
        ;;
esac

echo ""
