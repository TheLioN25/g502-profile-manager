#!/usr/bin/env bash
# Script para desinstalar ejecutables 'g502' y 'g502-gui' de ~/.local/bin
set -e

BIN_DIR="${HOME}/.local/bin"

removed=0
if [ -f "${BIN_DIR}/g502" ]; then
    rm -f "${BIN_DIR}/g502"
    echo "• Eliminado: ${BIN_DIR}/g502"
    removed=1
fi

if [ -f "${BIN_DIR}/g502-gui" ]; then
    rm -f "${BIN_DIR}/g502-gui"
    echo "• Eliminado: ${BIN_DIR}/g502-gui"
    removed=1
fi

if [ "$removed" -eq 1 ]; then
    echo ""
    echo "✓ Ejecutables 'g502' y 'g502-gui' desinstalados correctamente de ~/.local/bin."
else
    echo "No se encontraron binarios instalados en ~/.local/bin."
fi
