import subprocess
import time

subprocess.run(["sudo", "systemctl", "stop", "klipperlcd.service"])
subprocess.Popen(["sudo", "python3", "/home/pi/KlipperLCD/firmw2.py"])
#try:
    #pid = subprocess.check_output(
        #["pgrep", "-f", "/home/pi/KlipperLCD/main.py"],
        #text=True
    #).strip()
    #if pid:
        #subprocess.run(["sudo", "kill", pid])
#except:
    #pass
