import serial
import time
import os
import subprocess
import glob
import sys

FILE_PATH = '/home/pi/KlipperLCD/LCD.tft'
DOWNLOAD_BAUD = 921600
USADO_SUFFIX = "usado"

def find_port():
    possible_ports = []
    possible_ports.extend(glob.glob('/dev/ttyUSB*'))
    possible_ports.extend(glob.glob('/dev/ttyACM*'))
    for candidate in ['/dev/ttyAMA0', '/dev/ttyS0', '/dev/serial0']:
        if os.path.exists(candidate):
            possible_ports.append(candidate)

    for port in possible_ports:
        try:
            with serial.Serial(port, 921600, timeout=0.1) as ser:
                return port
        except:
            continue
    return None

def connect_to_screen(port):
    baud = 921600
    try:
        with serial.Serial(port, baud, timeout=0.1) as ser:
            connect_cmd = bytes.fromhex(
                "44 52 41 4B 4A 48 53 55 59 44 47 42 4E 43 4A 48 47 4A 4B 53 48 42 44 4E FF FF FF 00 FF FF FF 63 6F 6E 6E 65 63 74 FF FF FF"
            )
            ser.write(connect_cmd)
            time.sleep((1000000/baud+30)/1000)
            response = ser.read(1024)
            if b'comok' in response:
                return baud
    except:
        pass
    return None

def send_download_command(port, file_path, connect_baud, download_baud):
    real_file_path = os.path.realpath(file_path)
    file_size = os.path.getsize(real_file_path)

    with serial.Serial(port, connect_baud) as ser:
        cmd = f"whmi-wri {file_size},{download_baud},0".encode()
        ser.write(cmd + b'\xff\xff\xff')
        time.sleep(0.35)
        ser.baudrate = download_baud
        response = ser.read(1)
        if response != b'\x05':
            return False
        with open(real_file_path, 'rb') as f:
            while True:
                chunk = f.read(4096)
                if not chunk:
                    break
                ser.write(chunk)
                while True:
                    resp = ser.read(1)
                    if resp == b'\x05':
                        break
    return True

def mark_as_used():
    if not os.path.exists(FILE_PATH):
        return
    current_tft_path = os.path.realpath(FILE_PATH)
    base_name = os.path.basename(current_tft_path).replace(".tft", "")
    new_file_name = f"{base_name}{USADO_SUFFIX}.tft"
    new_tft_path = os.path.join(os.path.dirname(current_tft_path), new_file_name)
    os.rename(current_tft_path, new_tft_path)
    os.remove(FILE_PATH)
    os.symlink(new_tft_path, FILE_PATH)

def main():
    port = find_port()
    if not port:
        print("❌ No se pudo encontrar puerto serie para la pantalla.")
        return

    try:
        # 1. Detener KlipperLCD
        subprocess.run(["systemctl", "stop", "KlipperLCD.service"], check=True)
        time.sleep(1)

        # 2. Intentar conectar y actualizar
        connect_baud = connect_to_screen(port)
        update_success = False
        if connect_baud:
            update_success = send_download_command(port, FILE_PATH, connect_baud, DOWNLOAD_BAUD)

        # 3. Marcar como usado si fue bien
        if update_success:
            print("✅ Firmware actualizado correctamente.")
            mark_as_used()
        else:
            print("⚠️ No se pudo actualizar firmware.")

    finally:
        # 4. Siempre volver a levantar KlipperLCD
        time.sleep(2)
        subprocess.run(["systemctl", "start", "KlipperLCD.service"])

if __name__ == "__main__":
    main()
