#!/bin/bash
set -e

# <-- CORRECCIÓN 1: Comprobar si se ejecuta como root (sudo)
if [ "$EUID" -ne 0 ]; then
  echo "Error: Por favor, ejecuta este script como root o con sudo."
  exit 1
fi

# <-- CORRECCIÓN 2: Usar variables para todas las rutas
PI_HOME="/home/pi"
KLIPPERLCD_DIR="$PI_HOME/KlipperLCD"
PRINTER_DATA_DIR="$PI_HOME/printer_data"
MOONRAKER_ASVC="$PRINTER_DATA_DIR/moonraker.asvc"
MOONRAKER_CONF="$PRINTER_DATA_DIR/config/moonraker.conf"

# 1. Detener servicio y eliminar systemd
if [ -d "$KLIPPERLCD_DIR" ]; then
    echo "=== Deteniendo servicio KlipperLCD ==="
    systemctl stop KlipperLCD.service || true
    systemctl disable KlipperLCD.service || true

    echo "=== Eliminando servicio systemd ==="
    rm -f /etc/systemd/system/KlipperLCD.service
    systemctl daemon-reload
else
    echo "== Carpeta KlipperLCD no encontrada, saltando servicio =="
fi

# 2. Cambiar a directorio seguro antes de borrar
cd "$PI_HOME" || exit 1

# 3. Eliminar la carpeta KlipperLCD
echo "=== Eliminando carpeta KlipperLCD ==="
rm -rf "$KLIPPERLCD_DIR"

# 4. Limpiar referencias externas (Moonraker)
echo "=== Limpiando configuración en Moonraker ==="

# Eliminar línea del fichero de servicios
if [ -f "$MOONRAKER_ASVC" ]; then
    sed -i '/KlipperLCD/d' "$MOONRAKER_ASVC"
fi

# Eliminar sección del fichero de configuración
if [ -f "$MOONRAKER_CONF" ]; then
    # <-- CORRECCIÓN 3: Comando sed mejorado
    # Este comando elimina desde '[update_manager KlipperLCD]' hasta la siguiente
    # sección que empiece por '[' o hasta el final del archivo si no hay más.
    # Es más seguro que depender de una línea en blanco.
    sed -i '/^\[update_manager KlipperLCD\]/,/^\s*\[/{/^\s*\[/!d}' "$MOONRAKER_CONF"
fi

systemctl restart moonraker

echo "=== Desinstalación completada ==="
