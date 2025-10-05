import os
import getopt
import sys
import time
import base64
import subprocess
from threading import Thread
from datetime import timedelta

import glob
import serial

from printer import PrinterData
from lcd import LCD, _printerData

def find_port():
    possible_ports = []
    possible_ports.extend(glob.glob('/dev/ttyUSB*'))
    possible_ports.extend(glob.glob('/dev/ttyACM*'))
    if os.path.exists('/dev/ttyAMA0'):
        possible_ports.append('/dev/ttyAMA0')
    if os.path.exists('/dev/ttyS0'):
        possible_ports.append('/dev/ttyS0')
    if os.path.exists('/dev/serial0'):
        possible_ports.append('/dev/serial0')

    for port in possible_ports:
        try:
            with serial.Serial(port, 921600, timeout=0.1) as ser:                                                             return port
        except:
            continue
    return None

class KlipperLCD ():
    def __init__(self):

        port = find_port()
        if not port:
            raise Exception("No se encontró ningún puerto válido para la pantalla")
        self.lcd = LCD(port, callback=self.lcd_callback)

        #self.lcd = LCD("/dev/ttyUSB0", callback=self.lcd_callback)
        self.lcd.start()
        self.printer = PrinterData('XXXXXX', URL=("127.0.0.1"), klippy_sock='/home/pi/printer_data/comms/klippy.sock', callback=self.printer_callback, lcd_instance=self.lcd)
        self.running = False
        self.wait_probe = False
        self.thumbnail_inprogress = False

        progress_bar = 1
        while self.printer.update_variable() == False:
            progress_bar += 5
            self.lcd.boot_progress(progress_bar)
            time.sleep(1)

        self.printer.init_Webservices()
        gcode_store = self.printer.get_gcode_store()
        self.lcd.write_gcode_store(gcode_store)

        macros = self.printer.get_macros()
        self.lcd.write_macros(macros)

        print(self.printer.MACHINE_SIZE)
        print(self.printer.SHORT_BUILD_VERSION)
        self.lcd.about_machine(self.printer.MACHINE_SIZE, self.printer.SHORT_BUILD_VERSION)

        mem_addr = 150
        if self.printer.MACHINE_SIZE == "300x300x400":
            new_val = 2
        elif self.printer.MACHINE_SIZE == "240x240x260":
            new_val = 1
        else:
            new_val = 0

        current_val = self.lcd.read_value("boot.va2.val")
        print(f"current_val ({type(current_val)}):", current_val, "new_val:", new_val)

        if current_val != new_val:
            self.lcd.write(f"boot.va2.val={new_val}")
            self.lcd.write(f"wepo boot.va2.val,{mem_addr}")
        self.lcd.write("page main")


    def start(self):
        print("KlipperLCD start")
        self.running = True
        #self.lcd.start()
        Thread(target=self.periodic_update).start()

    def periodic_update(self):
        while self.running:
            if self.wait_probe:
                print("Zpos=%f, Zoff=%f" % (self.printer.current_position.z, self.printer.BABY_Z_VAR))
                if self.printer.ishomed():
                        self.wait_probe = False
                        print("IsHomed")
                        self.lcd.probe_mode_start()

            self.printer.update_variable()
            data = _printerData()
            data.hotend_target = self.printer.thermalManager['temp_hotend'][0]['target']
            data.hotend        = self.printer.thermalManager['temp_hotend'][0]['celsius']
            data.bed_target    = self.printer.thermalManager['temp_bed']['target']
            data.bed           = self.printer.thermalManager['temp_bed']['celsius']
            data.state         = self.printer.getState()
            data.percent       = self.printer.getPercent()
            duration = self.printer.print_duration
            if duration > 0:
                total_minutes = round(duration / 60)
                hours = total_minutes // 60
                minutes = total_minutes % 60
                data.duration = f"{int(hours)}h {int(minutes)}m"
            else:
                data.duration = "0h 0m"
            data.current_layer = self.printer.current_layer
            data.total_layer   = self.printer.total_layer
            data.remaining     = self.printer.remain()
            data.feedrate      = self.printer.print_speed
            data.flowrate      = self.printer.flow_percentage
            data.fan           = self.printer.thermalManager['fan_speed'][0]
            data.light         = self.printer.light_percentage
            data.light1        = self.printer.light1_percentage
            data.neo_r         = self.printer.neopixel_r
            data.neo_g         = self.printer.neopixel_g
            data.neo_b         = self.printer.neopixel_b
            data.filament_detected       = self.printer.filament_detected
            data.filament_sensor_enabled = self.printer.filament_sensor_enabled
            data.x_pos         = self.printer.current_position.x
            data.y_pos         = self.printer.current_position.y
            data.z_pos         = self.printer.current_position.z
            data.z_offset      = self.printer.BABY_Z_VAR
            data.MACHINE_SIZE  = self.printer.MACHINE_SIZE
            data.file_name     = self.printer.file_name
            data.max_velocity           = self.printer.max_velocity
            data.max_accel              = self.printer.max_accel
            data.minimum_cruise_ratio   = self.printer.minimum_cruise_ratio
            data.square_corner_velocity = self.printer.square_corner_velocity
            data.pressure_advance       = int (self.printer.pressure_advance)
            data.extrude_mintemp = self.printer.EXTRUDE_MINTEMP

            self.lcd.data_update(data)

            FLAG_FILE = "/tmp/.klipperlcd_fw_update"

            if os.path.exists(FLAG_FILE):
                self.lcd.send_wait_variable()
                subprocess.run(["rm", FLAG_FILE], check=True)


            time.sleep(2)

    def printer_callback(self, data, data_type):

        if data_type == 'response' and data.startswith("RESPOND"):
            try:
                 if "MSG=" in data:
                     message_part = data.split("MSG=", 1)[1]
                     message_to_send = message_part.strip().strip('"')
                     self.lcd.write(message_to_send)
                     return
            except Exception as e:
                print(f"Error al procesar el mensaje personalizado: {e}")

        if data_type == 'response' and "jose" in data:
            self.lcd.write("page adjustspeed")
        if data_type == 'response' and "main" in data:
            self.lcd.write("page adjustzoffset")
        if data_type == 'response' and "boot" in data:
            self.lcd.write("page boot")
        if data_type == 'response' and "beep" in data:
            self.lcd.write("beep 1000")
            return


        msg = self.lcd.format_console_data(data, data_type)
        if msg:
            self.lcd.write_console(msg)


        if 'status' in data:
            if 'print_stats' in data['status']:
                print_stats = data['status']['print_stats']
                if 'print_duration' in print_stats:
                    self.printer.print_duration = print_stats['print_duration']
                if 'info' in print_stats:
                    if 'current_layer' in print_stats['info']:
                        self.printer.current_layer = print_stats['info']['current_layer']
                    if 'total_layer' in print_stats['info']:
                        self.printer.total_layer = print_stats['info']['total_layer']

        if data_type == "screws_tilt":
            screws = data
            self.lcd.show_screws_data(screws)

        if data_type == "bed_mesh":
            self.lcd.show_bed_mesh(data)

        if data_type == "lcd_command":
            self.lcd.write(data)



    def show_thumbnail(self):
        if self.printer.file_path and (self.printer.file_name or self.lcd.files[self.lcd.selected_file]):
            file_name = ""
            if self.lcd.files:
                file_name = self.lcd.files[self.lcd.selected_file]
            elif self.printer.file_name:
                file_name = self.printer.file_name
            else:
                print("ERROR: gcode file not known")

            file = self.printer.file_path + "/" + file_name
            absolute_file_path = file.replace('~', '/home/pi') 

            # Reading file
            print(absolute_file_path)
            f = open(absolute_file_path, "r")
            if not f:
                f.close()
                print("File could not be opened: %s" % file)
                return
            buf = f.readlines()
            if not f:
                f.close()
                print("File could not be read")
                return

            f.close()
            thumbnail_found = False
            b64 = ""

            for line in buf:
                if 'thumbnail begin' in line:
                    thumbnail_found = True
                elif 'thumbnail end' in line:
                    thumbnail_found = False
                    break
                elif thumbnail_found:
                    b64 += line.strip(' \t\n\r;')
        
            if len(b64):
                # Decode Base64
                img = base64.b64decode(b64)        
                
                #Write thumbnail to LCD
                self.lcd.write_thumbnail(img)
            else:
                self.lcd.clear_thumbnail()
                print("Aborting thumbnail, no image found")
        else:
            print("File path or name to gcode-files missing")
        
        self.thumbnail_inprogress = False

    def lcd_callback(self, evt, data=None):
        if evt == self.lcd.evt.HOME:
            self.printer.home(data)

        elif evt == self.lcd.evt.MOVE_X:
            if self.printer.query_homed():
                self.printer.moveRelative('X', data, 4000)
            else:
                self.lcd.write("warn_move.va3.val=1")
                self.lcd.write("page warn_move")

        elif evt == self.lcd.evt.MOVE_Y:
            if self.printer.query_homed():
                self.printer.moveRelative('Y', data, 4000)
            else:
                self.lcd.write("warn_move.va3.val=1")
                self.lcd.write("page warn_move")

        elif evt == self.lcd.evt.MOVE_Z:
            if self.printer.query_homed():
                self.printer.moveRelative('Z', data, 600)
            else:
                self.lcd.write("warn_move.va3.val=1")
                self.lcd.write("page warn_move")

        elif evt == self.lcd.evt.MOVE_E:
            print(data)
            self.printer.moveRelative('E', data[0], data[1])
        elif evt == self.lcd.evt.Z_OFFSET:
            self.printer.setZOffset(data)
        elif evt == self.lcd.evt.NOZZLE:
            self.printer.setExtTemp(data)
        elif evt == self.lcd.evt.BED:
            self.printer.setBedTemp(data)
        elif evt == self.lcd.evt.FILES:
            files = self.printer.GetFiles(True)
            return files
        elif evt == self.lcd.evt.PRINT_START:
            self.printer.openAndPrintFile(data)
            if self.thumbnail_inprogress == False:
                self.thumbnail_inprogress = True
        elif evt == self.lcd.evt.THUMBNAIL:
            if self.thumbnail_inprogress == False:
                self.thumbnail_inprogress = True
                Thread(target=self.show_thumbnail).start()
        elif evt == self.lcd.evt.PRINT_STATUS:
            pass
        elif evt == self.lcd.evt.PRINT_STOP:
            self.printer.cancel_job()
        elif evt == self.lcd.evt.PRINT_PAUSE:
            self.printer.pause_job()
        elif evt == self.lcd.evt.PRINT_RESUME:
            self.printer.resume_job()
        elif evt == self.lcd.evt.PRINT_SPEED:
            self.printer.set_print_speed(data)
        elif evt == self.lcd.evt.FLOW:
            self.printer.set_flow(data)
        elif evt == self.lcd.evt.PROBE:
            if data is None:
                self.printer.sendGCode("G28")
                self.printer.sendGCode("PROBE_CALIBRATE")
            else:
                self.printer.probe_adjust(data)
        elif evt == self.lcd.evt.BABYSTEP:
            self.printer.baby_step(data)

        #elif evt == self.lcd.evt.BED_MESH:
            #pass
        elif evt == self.lcd.evt.LIGHT:
            self.printer.set_light(data)
        elif evt == self.lcd.evt.LIGHT1:
            self.printer.set_light1()
        elif evt == self.lcd.evt.FAN:
            self.printer.set_fan(data)
        elif evt == self.lcd.evt.FILAMENT_SENSOR:
            self.printer.set_filament_sensor(data)
        elif evt == self.lcd.evt.MOTOR_OFF:
            self.printer.sendGCode('M18')
        elif evt == self.lcd.evt.ACCEL:
            self.printer.sendGCode("SET_VELOCITY_LIMIT ACCEL=%d" % data)
        elif evt == self.lcd.evt.MINIMUM_CRUISE_RATIO:
            self.printer.sendGCode("SET_VELOCITY_LIMIT MINIMUM_CRUISE_RATIO=%.3f" % data)
        elif evt == self.lcd.evt.VELOCITY:
            self.printer.sendGCode("SET_VELOCITY_LIMIT VELOCITY=%d" % data)
        elif evt == self.lcd.evt.SQUARE_CORNER_VELOCITY:
            self.printer.sendGCode("SET_VELOCITY_LIMIT SQUARE_CORNER_VELOCITY=%.1f" % data)
        elif evt == self.lcd.evt.PRESSURE_ADVANCE:
            self.printer.sendGCode("SET_PRESSURE_ADVANCE ADVANCE=%.3f" % data)
        elif evt == self.lcd.evt.CONSOLE:
            if data == "BED_MESH_CALIBRATE":
                self.printer.waiting_bedmesh = True
                self.printer.sendGCode('G28')
            self.printer.sendGCode(data)
        elif evt == self.lcd.evt.REBOOT_PI:
            self.printer.reboot_pi()
        elif evt == self.lcd.evt.SHUTDOWN_PI:
            self.printer.shutdown_pi()
        elif evt == self.lcd.evt.RESTART_LCD:
            self.printer.restart_klipperlcd()
        elif evt == self.lcd.evt.STOP_LCD:
            self.printer.stop_klipperlcd()
        elif evt == self.lcd.evt.SCREWS_TILT:
            self.printer.run_screws_tilt()
        elif evt == self.lcd.evt.EMERGENCY_STOP:
            self.printer.emergency_stop()


        else:
            print("lcd_callback event not recognised %d" % evt)

if __name__ == "__main__":

    x = KlipperLCD()
    x.start()







