#!/usr/bin/env bash
# Script para instalar ejecutables de usuario 'g502' y 'g502-gui' en ~/.local/bin
set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN_DIR="${HOME}/.local/bin"

mkdir -p "${BIN_DIR}"

# 1. Crear script lanzador para CLI (g502)
cat << 'EOF_INNER' > "${BIN_DIR}/g502"
#!/usr/bin/env bash
REPO_ROOT_RESOLVED="@REPO_ROOT@"
exec python3 "${REPO_ROOT_RESOLVED}/src/cli.py" "$@"
EOF_INNER
sed -i "s|@REPO_ROOT@|${REPO_ROOT}|g" "${BIN_DIR}/g502"
chmod +x "${BIN_DIR}/g502"
echo "• Ejecutable CLI instalado en: ${BIN_DIR}/g502"

# 2. Crear script lanzador para GUI (g502-gui)
cat << 'EOF_INNER' > "${BIN_DIR}/g502-gui"
#!/usr/bin/env bash
REPO_ROOT_RESOLVED="@REPO_ROOT@"
exec python3 "${REPO_ROOT_RESOLVED}/src/gui/app.py" "$@"
EOF_INNER
sed -i "s|@REPO_ROOT@|${REPO_ROOT}|g" "${BIN_DIR}/g502-gui"
chmod +x "${BIN_DIR}/g502-gui"
echo "• Ejecutable GUI instalado en: ${BIN_DIR}/g502-gui"

# 3. Detección automática regional de idioma en primera instalación
if [ ! -f "${HOME}/.config/g502-preferences.json" ]; then
    echo ""
    "${REPO_ROOT}/scripts/detect-locale.sh" --apply
fi

echo ""
echo "✓ ¡Binarios instalados con éxito!"
echo "  Ahora puedes ejecutar directamente en cualquier terminal:"
echo "  - g502 --help"
echo "  - g502 list"
echo "  - g502 export"
echo "  - g502-gui"
