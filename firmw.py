import serial
import time
import os
import subprocess
import glob

PORT = '/dev/ttyUSB0'
FILE_PATH = '/home/pi/KlipperLCD/LCD.tft'
DOWNLOAD_BAUD = 921600
USADO_SUFFIX = "usado"

def connect_to_screen(port):
    connect_bauds = [9600,115200,19200,38400,57600,230400,256000,512000,921600,4800,2400]
    for baud in connect_bauds:
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
            continue
    return None

def send_download_command(port, file_path, connect_baud, download_baud):
    # CORRECCIÓN: Resolver el symlink a la ruta real antes de usar os.path.getsize
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
    subprocess.run(["sudo", "systemctl", "stop", "klipperlcd.service"])
    time.sleep(1)

    connect_baud = connect_to_screen(PORT)

    update_success = False
    if connect_baud:
        update_success = send_download_command(PORT, FILE_PATH, connect_baud, DOWNLOAD_BAUD)

    if update_success:
        mark_as_used()

    time.sleep(4)
    subprocess.run(["sudo", "systemctl", "start", "klipperlcd.service"])

if __name__ == "__main__":
    main()
