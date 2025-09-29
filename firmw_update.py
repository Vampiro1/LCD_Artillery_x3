import os
import requests
import subprocess
import glob
from datetime import datetime
from io import BytesIO
from zipfile import ZipFile

GITHUB_USER = "Vampiro1"
GITHUB_REPO = "LCD_Artillery_x3"
FIRMWARE_FOLDER = "/home/pi/KlipperLCD/firmware"
LOCAL_SYMLINK = "/home/pi/KlipperLCD/LCD.tft"
FLAG_FILE = "/tmp/.klipperlcd_fw_update"
USADO_SUFFIX = "usado"

RELEASE_URL = "https://github.com/Vampiro1/LCD_Artillery_x3/releases/download/firmware/141025.zip"

def parse_version_to_date(version_str):
    try:
        is_used = version_str.endswith(USADO_SUFFIX)
        if is_used:
            version_str = version_str.replace(USADO_SUFFIX, "")
        dt = datetime.strptime(version_str, "%d%m%y")
        return dt
    except ValueError:
        return datetime(1900, 1, 1)

def get_latest_remote_firmware():
    print("--- INICIO DE VERIFICACIÓN REMOTA ---")
    try:
        r = requests.get(RELEASE_URL)
        r.raise_for_status()
        zip_bytes = BytesIO(r.content)
        with ZipFile(zip_bytes) as z:
            tft_files = [f for f in z.namelist() if f.endswith(".tft") and f.replace(".tft","").isdigit()]
            if not tft_files:
                print("ERROR: No se encontraron archivos .tft válidos en el release.")
                return None
            tft_files.sort(key=lambda x: parse_version_to_date(x.replace(".tft","")))
            latest_name = tft_files[-1]
            latest_data = z.read(latest_name)
            return latest_name, latest_data
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Fallo de conexión al release: {e}")
        return None

def create_flag():
    subprocess.run(["sudo", "touch", FLAG_FILE], check=True)

def cleanup_firmware_files():
    for f in glob.glob(os.path.join(FIRMWARE_FOLDER, "*.tft")):
        os.remove(f)

def main():
    os.makedirs(FIRMWARE_FOLDER, exist_ok=True)
    latest = get_latest_remote_firmware()
    if not latest:
        return

    latest_name, latest_data = latest
    remote_version_str = latest_name.replace(".tft", "")
    remote_date = parse_version_to_date(remote_version_str)

    local_version_str = "N/A"
    is_local_used = False
    local_date = datetime(1900, 1, 1)

    if os.path.exists(LOCAL_SYMLINK):
        local_target = os.readlink(LOCAL_SYMLINK)
        local_file_name = os.path.basename(local_target)
        local_version_str = local_file_name.replace(".tft","")
        local_date = parse_version_to_date(local_version_str)
        if local_version_str.endswith(USADO_SUFFIX):
            is_local_used = True

    if remote_date < local_date:
        return
    if remote_date == local_date and is_local_used:
        return

    # actualización requerida
    cleanup_firmware_files()
    local_path = os.path.join(FIRMWARE_FOLDER, latest_name)
    with open(local_path, "wb") as f:
        f.write(latest_data)

    subprocess.run(["sudo", "rm", "-f", LOCAL_SYMLINK], check=False)
    subprocess.run(["sudo", "ln", "-s", local_path, LOCAL_SYMLINK], check=True)

    create_flag()

if __name__ == "__main__":
    main()
