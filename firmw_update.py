import os
import requests
import subprocess
import glob
from datetime import datetime

GITHUB_USER = "Vampiro1"
GITHUB_REPO = "Pantalla-artillery-x3-"
FIRMWARE_FOLDER = "/home/pi/KlipperLCD/firmware"
LOCAL_SYMLINK = "/home/pi/KlipperLCD/LCD.tft"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/firmware"
FLAG_FILE = "/tmp/.klipperlcd_fw_update"
USADO_SUFFIX = "usado"

def parse_version_to_date(version_str):
    try:
        is_used = version_str.endswith(USADO_SUFFIX)
        if is_used:
            version_str = version_str.replace(USADO_SUFFIX, "")

        dt = datetime.strptime(version_str, "%d%m%y")
        print(f"DEBUG: '{version_str}' -> Fecha: {dt.date()} (Usado: {is_used})")
        return dt
    except ValueError:
        dt_default = datetime(1900, 1, 1)
        print(f"DEBUG: Fallo al parsear '{version_str}'. Usando fecha por defecto: {dt_default.date()}")
        return dt_default

def get_latest_remote_firmware():
    print("--- INICIO DE VERIFICACIÓN REMOTA ---")
    try:
        r = requests.get(GITHUB_API_URL)
        r.raise_for_status()
        files = r.json()
        tft_files = [f for f in files if f["name"].endswith(".tft")]
        if not tft_files:
            print("ERROR: No se encontraron archivos .tft remotos.")
            return None
        
        tft_files.sort(key=lambda x: parse_version_to_date(x["name"].replace(".tft", "")))
        
        latest = tft_files[-1]
        print(f"ÉXITO: Versión remota encontrada: {latest['name']}")
        return latest
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Fallo de conexión a GitHub: {e}")
        return None

def create_flag():
    print(f"ACCIÓN: Creando bandera con sudo en {FLAG_FILE}")
    subprocess.run(["sudo", "touch", FLAG_FILE], check=True)
    print("FIN: Bandera de actualización creada con éxito.")

def cleanup_firmware_files():
    print("ACCIÓN: Limpiando archivos .tft antiguos.")
    for f in glob.glob(os.path.join(FIRMWARE_FOLDER, "*.tft")):
        print(f"  -> Borrando: {f}")
        os.remove(f)
    print("Limpieza finalizada.")

def main():
    print(f"INICIO: Ejecutando {os.path.basename(__file__)}")
    os.makedirs(FIRMWARE_FOLDER, exist_ok=True)
    latest = get_latest_remote_firmware()

    if not latest:
        print("FIN: No hay versión remota válida. Saliendo.")
        return

    remote_version_str = latest["name"].replace(".tft", "")
    remote_date = parse_version_to_date(remote_version_str)

    local_version_str = "N/A"
    is_local_used = False
    local_date = datetime(1900, 1, 1)

    print("\n--- VERIFICACIÓN LOCAL ---")
    if os.path.exists(LOCAL_SYMLINK):
        local_target = os.readlink(LOCAL_SYMLINK)
        local_file_name = os.path.basename(local_target)
        local_version_str = local_file_name.replace(".tft","")
        local_date = parse_version_to_date(local_version_str)

        print(f"INFO: Symlink '{LOCAL_SYMLINK}' apunta a: {local_target}")
        print(f"INFO: Nombre de archivo local: {local_file_name}")

        if local_version_str.endswith(USADO_SUFFIX):
            is_local_used = True

    else:
        print(f"INFO: No existe el Symlink '{LOCAL_SYMLINK}'. Se procederá a la descarga.")

    print("\n--- COMPARACIÓN DE VERSIONES ---")
    print(f"Remota: {remote_date.date()} (Cadena: {remote_version_str})")
    print(f"Local: {local_date.date()} (Usado: {is_local_used})")

    if remote_date < local_date:
        print("DECISIÓN: Versión remota más antigua que la local. Saliendo.")
        return

    if remote_date == local_date and is_local_used:
        print("DECISIÓN: Versión local actual e instalada correctamente. Saliendo.")
        return

    print("DECISIÓN: ***ACTUALIZACIÓN REQUERIDA.***")

    cleanup_firmware_files()

    download_url = latest["download_url"]
    local_path = os.path.join(FIRMWARE_FOLDER, latest["name"])

    print(f"\nACCIÓN: Descargando {latest['name']} de {download_url}")
    try:
        r = requests.get(download_url)
        r.raise_for_status()
        with open(local_path, "wb") as f:
            f.write(r.content)
        print("ÉXITO: Descarga completada.")
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Fallo durante la descarga: {e}. Saliendo.")
        return

    print(f"ACCIÓN: Creando/actualizando symlink '{LOCAL_SYMLINK}' para que apunte a '{local_path}'")
    subprocess.run(["sudo", "rm", "-f", LOCAL_SYMLINK], check=False)
    subprocess.run(["sudo", "ln", "-s", local_path, LOCAL_SYMLINK], check=True)
    print("Symlink actualizado.")

    create_flag()

if __name__ == "__main__":
    main()
