set -e

if [ "$EUID" -ne 0 ]; then
  echo "Error: Por favor, ejecuta este script como root o con sudo."
  exit 1
fi

PI_HOME="/home/pi"
KLIPPERLCD_DIR="$PI_HOME/KlipperLCD"
PRINTER_DATA_DIR="$PI_HOME/printer_data"
MOONRAKER_ASVC="$PRINTER_DATA_DIR/moonraker.asvc"
MOONRAKER_CONF="$PRINTER_DATA_DIR/config/moonraker.conf"

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

cd "$PI_HOME" || exit 1

echo "=== Eliminando carpeta KlipperLCD ==="
rm -rf "$KLIPPERLCD_DIR"

echo "=== Limpiando configuración en Moonraker ==="

MOONRAKER_ASVC="/home/pi/printer_data/moonraker.asvc"
MOONRAKER_CONF="/home/pi/printer_data/config/moonraker.conf"

if [ -f "$MOONRAKER_ASVC" ]; then
    sudo sed -i '/KlipperLCD/d' "$MOONRAKER_ASVC"
fi

if [ -f "$MOONRAKER_CONF" ]; then
    sudo sed -i '/^\[update_manager KlipperLCD\]/,/^\s*\[/{/^\s*\[/!d}' "$MOONRAKER_CONF"
    sudo sed -i '/KlipperLCD/d' "$MOONRAKER_CONF"
fi

sudo systemctl restart moonraker

systemctl restart moonraker

echo "=== Desinstalación completada ==="
