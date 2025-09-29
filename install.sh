#!/bin/bash
set -e

echo "=== Instalando dependencias ==="
sudo apt-get update
sudo apt-get install -y python3-pip git unzip wget
pip3 install --upgrade pip
pip3 install pyserial

echo "=== Clonando repositorio ==="
if [ ! -d "/home/pi/KlipperLCD" ]; then
    git clone https://github.com/Vampiro1/LCD_Artillery_x3 /home/pi/KlipperLCD
fi
cd /home/pi/KlipperLCD

echo "=== Preparando firmware ==="
FIRMWARE_DEST="/home/pi/KlipperLCD/firmware"
mkdir -p "$FIRMWARE_DEST"

wget -O "$FIRMWARE_DEST/141025.zip" "https://github.com/Vampiro1/LCD_Artillery_x3/releases/download/firmware/141025.zip"
unzip -o "$FIRMWARE_DEST/141025.zip" -d "$FIRMWARE_DEST"
rm "$FIRMWARE_DEST/141025.zip"

ln -sf /home/pi/KlipperLCD/firmware/141025usado.tft /home/pi/KlipperLCD/LCD.tft

echo "=== Instalando servicio systemd ==="
sudo cp KlipperLCD.service /etc/systemd/system/KlipperLCD.service
sudo chmod 644 /etc/systemd/system/KlipperLCD.service
sudo systemctl daemon-reload
sudo systemctl enable KlipperLCD.service
sudo systemctl start KlipperLCD.service

echo "=== Configurando Moonraker ==="
MOONRAKER_ASVC=/home/pi/printer_data/moonraker.asvc
grep -qxF "KlipperLCD" $MOONRAKER_ASVC || echo "KlipperLCD" | sudo tee -a $MOONRAKER_ASVC > /dev/null

CONF=/home/pi/printer_data/config/moonraker.conf
grep -q "\[update_manager KlipperLCD\]" $CONF || \
(sudo tee -a $CONF > /dev/null <<-EOL

[update_manager KlipperLCD]
type: git_repo
path: ~/KlipperLCD
origin: https://github.com/Vampiro1/LCD_Artillery_x3.git
branch: master
is_system_service: True
EOL
)

sudo systemctl restart moonraker

echo "=== Instalación completada ==="
