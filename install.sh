#!/bin/bash
set -e

echo "=== Instalando dependencias ==="
sudo apt-get update
sudo apt-get install -y python3-pip git unzip wget
pip3 install --upgrade pip
pip3 install pyserial

echo "=== Preparando firmware ==="
FIRMWARE_DEST="/home/pi/KlipperLCD/firmware"
mkdir -p "$FIRMWARE_DEST"

wget -O "$FIRMWARE_DEST/firmware.zip" "https://github.com/Vampiro1/LCD_Artillery_x3/releases/download/firmware/firmware.zip"
unzip -o "$FIRMWARE_DEST/firmware.zip" -d "$FIRMWARE_DEST"
rm "$FIRMWARE_DEST/firmware.zip"

ln -sf /home/pi/KlipperLCD/firmware/041025usado.tft /home/pi/KlipperLCD/LCD.tft

echo "=== Instalando servicio systemd ==="
sudo cp KlipperLCD.service /etc/systemd/system/KlipperLCD.service
sudo chmod 644 /etc/systemd/system/KlipperLCD.service

sudo cp firmw.service /etc/systemd/system/firmw.service
sudo chmod 644 /etc/systemd/system/firmw.service

sudo systemctl daemon-reload
sudo systemctl enable KlipperLCD.service

echo "=== Configurando Moonraker ==="
MOONRAKER_ASVC=/home/pi/printer_data/moonraker.asvc
CONF=/home/pi/printer_data/config/moonraker.conf

grep -qxF "KlipperLCD" $MOONRAKER_ASVC || echo "KlipperLCD" | sudo tee -a $MOONRAKER_ASVC > /dev/null

if [ -f "$CONF" ]; then
    echo "Eliminando rastros antiguos de KlipperLCD en moonraker.conf..."
    sudo sed -i '/KlipperLCD/d' "$CONF"
fi

sudo tee -a $CONF > /dev/null <<-EOL

[update_manager KlipperLCD]
type: git_repo
path: ~/KlipperLCD
origin: https://github.com/Vampiro1/LCD_Artillery_x3.git
primary_branch: master
channel: dev
is_system_service: True
EOL

sudo systemctl restart moonraker
sudo systemctl start KlipperLCD.service

echo "=== Instalación completada ==="
