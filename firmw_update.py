import os
import requests
import subprocess
import glob
import zipfile
from datetime import datetime

GITHUB_USER = "Vampiro1"
GITHUB_REPO = "Pantalla-artillery-x3-"
FIRMWARE_FOLDER = "/home/pi/KlipperLCD/firmware"
LOCAL_SYMLINK = "/home/pi/KlipperLCD/LCD.tft"
GITHUB_RELEASE_URL = f"https://github.com/{GITHUB_USER}/{GITHUB_REPO}/releases/download/firmware/141025.zip"
FLAG_FILE = "/tmp/.klipperlcd_fw_update"
USADO_SUFFIX = "usado"

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
    os.makedirs(FIRMWARE_FOLDER, exist_ok=True)
    zip_path = os.path.join(FIRMWARE_FOLDER, "latest.zip")
    r = requests.get(GITHUB_RELEASE_URL)
    r.raise_for_status()
    with open(zip_path, "wb") as f:
        f.write(r.content)
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(FIRMWARE_FOLDER)
        tft_files = [f for f in zip_ref.namelist() if f.endswith(".tft") and USADO_SUFFIX not in f]
        if not tft_files:
            return None
        tft_files.sort(key=lambda x: parse_version_to_date(os.path.splitext(os.path.basename(x))[0]))
        latest_name = os.path.basename(tft_files[-1])
        return latest_name

def create_flag():
    subprocess.run(["sudo", "touch", FLAG_FILE], check=True)

def cleanup_firmware_files():
    for f in glob.glob(os.path.join(FIRMWARE_FOLDER, "*.tft")):
        os.remove(f)

def main():
    os.makedirs(FIRMWARE_FOLDER, exist_ok=True)
    latest_name = get_latest_remote_firmware()
    if not latest_name:
        return
    remote_version_str = os.path.splitext(latest_name)[0]
    remote_date = parse_version_to_date(remote_version_str)
    local_version_str = "N/A"
    is_local_used = False
    local_date = datetime(1900, 1, 1)
    if os.path.exists(LOCAL_SYMLINK):
        local_target = os.readlink(LOCAL_SYMLINK)
        local_file_name = os.path.basename(local_target)
        local_version_str = os.path.splitext(local_file_name)[0]
        local_date = parse_version_to_date(local_version_str)
        if local_version_str.endswith(USADO_SUFFIX):
            is_local_used = True
    if remote_date < local_date:
        return
    if remote_date == local_date and is_local_used:
        return
    cleanup_firmware_files()
    local_path = os.path.join(FIRMWARE_FOLDER, latest_name)
    subprocess.run(["sudo", "rm", "-f", LOCAL_SYMLINK], check=False)
    subprocess.run(["sudo", "ln", "-s", local_path, LOCAL_SYMLINK], check=True)
    create_flag()

if __name__ == "__main__":
    main()
