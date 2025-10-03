#!/bin/bash
set -e

KLIPPERLCD_DIR="/home/pi/KlipperLCD"

# 1. Detener servicio y eliminar systemd
if [ -d "$KLIPPERLCD_DIR" ]; then
    echo "=== Deteniendo servicio KlipperLCD ==="
    sudo systemctl stop KlipperLCD.service || true
    sudo systemctl disable KlipperLCD.service || true

    echo "=== Eliminando servicio systemd ==="
    sudo rm -f /etc/systemd/system/KlipperLCD.service
    sudo systemctl daemon-reload
else
    echo "== Carpeta KlipperLCD no encontrada, saltando servicio =="
fi

# 2. Cambiar a directorio seguro antes de borrar
cd /home/pi || exit 1

# 3. Eliminar la carpeta KlipperLCD
echo "=== Eliminando carpeta KlipperLCD ==="
rm -rf "$KLIPPERLCD_DIR"

# 4. Limpiar referencias externas (Moonraker)
echo "=== Limpiando configuración en Moonraker ==="
MOONRAKER_ASVC=/home/pi/printer_data/moonraker.asvc
sudo sed -i '/KlipperLCD/d' $MOONRAKER_ASVC

CONF=/home/pi/printer_data/config/moonraker.conf
sudo sed -i '/\[update_manager KlipperLCD\]/,/^$/d' $CONF

echo "=== Desinstalación completada ==="
