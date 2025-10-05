def run(self):import binascii
from time import sleep
from threading import Thread
from array import array
from io import BytesIO
from PIL import Image
import lib_col_pic
import binascii
import subprocess
import atexit
import serial
import subprocess, json
import time

class LCD_var ():
    def __init__(self, ser, varname):
        self.ser = ser
        self.varname = varname

    def write_val(self, val):
        self.ser.write(self.varname.encode())
        self.ser.write(b'.val=')
        self.ser.write(str(val).encode())
        self.ser.write(bytearray([0xFF, 0xFF, 0xFF]))

    @property
    def val(self):
        return self._val

    @val.setter
    def val(self, val):
        self._val = val
        self.write_val(val)

FHONE = 0x5a
FHTWO = 0xa5
FHLEN = 0x06

MaxFileNumber = 25

RegAddr_W = 0x80
RegAddr_R = 0x81
CMD_WRITEVAR = 0x82
CMD_READVAR  = 0x83
CMD_CONSOLE  = 0x42

ExchangePageBase = 0x5A010000 # Unsigned long
StartSoundSet    = 0x060480A0
FONT_EEPROM      = 0

# variable addr
ExchangepageAddr = 0x0084
SoundAddr        = 0x00A0

RX_STATE_IDLE = 0
RX_STATE_READ_LEN = 1
RX_STATE_READ_CMD = 2
RX_STATE_READ_DAT = 3

PLA   = 0
ABS   = 1
PETG  = 2
TPU   = 3
PROBE = 4


class _printerData():
    hotend_target   = None
    hotend          = None
    bed_target      = None
    bed             = None
    current_layer   = 0
    total_layer     = 0


    extrude_mintemp = None

    state           = None

    percent         = None
    duration        = None
    remaining       = None
    feedrate        = None
    flowrate        = 0
    fan             = None
    light           = None
    light1          = None
    neopixel_r      = None
    neopixel_g      = None
    neopixel_b      = None
    filament_detected = None
    filament_sensor_enabled = None
    x_pos           = None
    y_pos           = None
    z_pos           = None
    z_offset        = None
    MACHINE_SIZE    = None
    file_name       = None
    max_velocity           = None
    max_accel              = None
    minimum_cruise_ratio   = None
    square_corner_velocity = None
    pressure_advance =  None
    BABY_Z_VAR      = 0

class LCDEvents():
    HOME           = 1
    MOVE_X         = 2
    MOVE_Y         = 3
    MOVE_Z         = 4
    MOVE_E         = 5
    NOZZLE         = 6
    BED            = 7
    FILES          = 8
    PRINT_START    = 9
    PRINT_STOP     = 10
    PRINT_PAUSE    = 11
    PRINT_RESUME   = 12
    PROBE          = 13
    BED_MESH       = 14
    LIGHT          = 15
    FAN            = 16
    MOTOR_OFF      = 17
    PRINT_STATUS   = 18 ## Not needed?
    PRINT_SPEED    = 19
    FLOW           = 20
    Z_OFFSET       = 21
    PROBE_COMPLETE = 22
    PROBE_BACK     = 23
    ACCEL          = 24
    MINIMUM_CRUISE_RATIO = 2
    VELOCITY       = 26
    SQUARE_CORNER_VELOCITY = 27
    THUMBNAIL        = 28
    CONSOLE          = 29
    FILAMENT_SENSOR  = 30
    LIGHT1           = 31
    PRESSURE_ADVANCE = 32
    REBOOT_PI        = 33
    SHUTDOWN_PI      = 34
    RESTART_LCD      = 35
    STOP_LCD         = 36
    START_LCD        = 37
    SCREWS_TILT      = 40
    EMERGENCY_STOP   = 41
    BABYSTEP         = 42


class LCD:
    def __init__(self, port=None, baud=921600, callback=None,):
        self.addr_func_map = {
            0x1002: self._MainPage,
            0x1004: self._Adjustment,
            0x1006: self._PrintSpeed,
            0x1008: self._StopPrint,
            0x100A: self._PausePrint,
            0x100C: self._ResumePrint,
            0x1026: self._ZOffset,
            0x1030: self._TempScreen,
            0x1032: self._CoolScreen,
            0x1034: self._Heater0TempEnter,
            0x1038: self._Heater1TempEnter,
            0x103A: self._HotBedTempEnter,
            0x103E: self._SettingScreen,
            0x1040: self._SettingBack,
            0x1044: self._BedLevelFun,
            0x1046: self._AxisPageSelect,
            0x1048: self._Xaxismove,
            0x104A: self._Yaxismove,
            0x104C: self._Zaxismove,
            0x104E: self._SelectExtruder,
            0x1054: self._Heater0LoadEnter,
            0x1056: self._FilamentLoad,
            0x1058: self._Heater1LoadEnter,
            0x105C: self._ComandosKlipper,
            0x105E: self._FilamentCheck,
            0x105F: self._PowerContinuePrint,
            0x1090: self._PrintSelectMode,
            0x1092: self._XhotendOffset,
            0x1094: self._YhotendOffset,
            0x1096: self._ZhotendOffset,
            0x1098: self._StoreMemory,
            0x2198: self._PrintFile,
            0x2199: self._SelectFile,
            0x110E: self._ChangePage,
            0x2200: self._SetPreNozzleTemp,
            0x2201: self._SetPreBedTemp,
            0x2202: self._HardwareTest,
            0X2203: self._Err_Control,
            0x4201: self._Console
        }

        self.evt = LCDEvents()
        self.callback = callback
        self.printer = _printerData()
        #self.real_printer = real_printer
        self.bandera = 0
                              # PLA, ABS, PETG, TPU, PROBE
        self.preset_temp     = [220, 245,  245, 220, 205]
        self.preset_bed_temp = [ 60, 100,   75,  60,  60]
        self.preset_index    = 0
        # UART communication parameters
        self.ser = serial.Serial()
        self.ser.port = port
        self.ser.baudrate = baud
        self.ser.timeout = None
        self.va0 = LCD_var(self.ser, 'va0')
        self.va1 = LCD_var(self.ser, 'va1')
        #self.status_led1 = LCD_var(self.ser, 'status_led1')
        #self.status_led2 = LCD_var(self.ser, 'status_led2')
        self.running = False
        self.rx_buf = bytearray()
        self.rx_data_cnt = 0
        self.rx_state = RX_STATE_IDLE
        self.error_from_lcd = False
        # List of GCode files
        self.files = False
        self.selected_file = False
        self.waiting = None
        # Adjusting temp and move axis params
        self.adjusting = 'Hotend'
        self.temp_unit = 10
        self.move_unit = 1
        self.load_len = 25
        self.feedrate_e = 300
        self.z_offset_unit = 0.01
        self.filament_sensor_enabled = None
        self.filament_detected = None
        # Adjusting speed
        self.speed_adjusting = None
        self.speed_unit = 10
        self.adjusting_max = False
        self.adjusting_max1 = False
        self.adjusting_max2 = False
        self.accel_unit = 100
        # Probe /Level mode
        self.probe_mode = False
        # Thumbnail
        self.is_thumbnail_written = False
        self.askprint = False
        self.waiting_for_value = False
        self.last_read_value = None
        atexit.register(self._atexit)

    def _atexit(self):
        self.ser.close()
        self.running = False

    def start(self, *args, **kwargs):
        self.running = True
        self.ser.open()
        Thread(target=self.run).start()

        self.write("page boot")
        self.write(b'com_star')
        self.write("boot.j0.val=1")
        #self.write("boot.t0.txt=\"Iniciando klipperLCD...\"")

    def boot_progress(self, progress):
        #self.write("boot.t0.txt=\"Esperando el servicio de klipper...\"")
        self.write("boot.j0.val=%d" % progress)

    def about_machine(self, size, fw):
        self.write("information.size.txt=\"%s\"" % size)
        self.write("information.sversion.txt=\"%s\"" % fw)

    def read_value(self, var):
        self.last_read_value = None
        self.waiting_for_value = True
        self.write(f"get {var}")

        timeout = time.time() + 2  # Timeout de 2 segundos
        while self.waiting_for_value and time.time() < timeout:
            time.sleep(0.05)

        if not self.waiting_for_value:
            print(f"[DEBUG PARSED] var='{var}' val={self.last_read_value}")
            return self.last_read_value
        else:
            print(f"[DEBUG TIMEOUT] No se recibió respuesta para '{var}'")
            self.waiting_for_value = False  # Resetear la bandera
            return None

    def write(self, data, eol=True, lf=False):
        dat = bytearray()
        if type(data) == str:
            #dat.extend(map(ord, data))
            dat.extend(data.encode('utf-8'))
        else:
            dat.extend(data)
        if lf:
            dat.extend(dat[-1:])
            dat.extend(dat[-1:])
            dat[len(dat)-2] = 10 #'\r'
            dat[len(dat)-3] = 13 #'\n'
        self.ser.write(dat)
        if eol:
            self.ser.write(bytearray([0xFF, 0xFF, 0xFF]))

    def clear_thumbnail(self):
        self.write("printpause.cp0.close()")
        self.write("printpause.cp0.aph=0")
        self.write("printpause.va0.txt=\"\"")
        self.write("printpause.va1.txt=\"\"")

    def write_thumbnail(self, img):
        # Clear screen
        self.clear_thumbnail()

        # Open as image
        im = Image.open(BytesIO(img))
        width, height = im.size
        if width != 160 or height != 160:
            im = im.resize((160, 160))
            width, height = im.size

        pixels = im.load()

        color16 = array('H')
        for i in range(height): #Height
            for j in range(width): #Width
                r, g, b, a = pixels[j, i]
                r = r >> 3
                g = g >> 2
                b = b >> 3
                rgb = (r << 11) | (g << 5) | b
                if rgb == 0x0000:
                    rgb = 0x4AF0
                color16.append(rgb)

        output_data = bytearray(height * width * 10)
        result_int = lib_col_pic.ColPic_EncodeStr(color16, width, height, output_data, width * height * 10, 1024)

        each_max = 512
        j = 0
        k = 0
        result = [bytearray()]
        for i in range(len(output_data)):
            if output_data[i] != 0:
                if j % each_max == 0:
                    result.append(bytearray())
                    k += 1
                result[k].append(output_data[i])
                j += 1

        # Send image to screen
        self.error_from_lcd = True
        while self.error_from_lcd == True:
            print("Write thumbnail to LCD")
            self.error_from_lcd = False

            # Clear screen
            self.clear_thumbnail()

            sleep(0.2)

            for bytes in result:
                self.write("printpause.cp0.aph=0")
                self.write("printpause.va0.txt=\"\"")#

                self.write("printpause.va0.txt=\"", eol = False)
                self.write(bytes, eol = False)
                self.write("\"")

                self.write(("printpause.va1.txt+=printpause.va0.txt"))
                sleep(0.02)

            sleep(0.2)
            self.write("printpause.cp0.aph=127")
            self.write("printpause.cp0.write(printpause.va1.txt)")
            self.is_thumbnail_written = True
            print("Write thumbnail to LCD done!")

        if self.askprint == True:
            self.write("askprint.cp0.aph=127")
            self.write("askprint.cp0.write(printpause.va1.txt)")

    def clear_console(self):
        self.write("console.buf.txt=\"\"")
        self.write("console.slt0.txt=\"\"")


    def format_console_data(self, msg, data_type):
        data = None
        if data_type == 'command':
            data = "> " + msg
        elif data_type == 'response':
            if 'B:' in msg and 'T0:' in msg:
                pass ## Filter out temperature responses
            else:
                data = msg.replace("// ", "")
                data = data.replace("??????", "?")
                data = data.replace("echo: ", "")
                data = "< " + data
        else:
            print("format_console_data: type unknown")

        return data

    def write_console(self, data):
        if "\"" in data:
            data = data.replace("\"", "'")

        if '\n' in data:
            data = data.replace("\n", "\r\n")

        self.write("console.buf.txt=\"%s\"" % data.encode('latin-1', 'replace').decode('latin-1'), lf = True)
        self.write("console.buf.txt+=console.slt0.txt")
        self.write("console.slt0.txt=console.buf.txt")

    def write_gcode_store(self, gcode_store):
        self.clear_console()
        for data in gcode_store:
            msg = self.format_console_data(data['message'], data['type'])
            if msg:
                self.write_console(msg)

    def write_macros(self, macros):
        self.write("macro.cb0.path=\"\"")
        for macro in macros:
            line_feed = True
            if macro == macros[-1]: #Last element, dont print with line feed
                line_feed = False
            self.write("macro.cb0.path+=\"%s\"" % macro, lf = line_feed)

    def data_update(self, data):
        #print("data.state: %s self.printer.state: %s" % (data.state, self.printer.state))
        if data.hotend_target != self.printer.hotend_target:
            self.write("pretemp.nozzle.txt=\"%d\"" % data.hotend_target)
        if data.bed_target != self.printer.bed_target:
            self.write("pretemp.bed.txt=\"%d\"" % data.bed_target)
        if data.hotend != self.printer.hotend or data.hotend_target != self.printer.hotend_target:
            self.write("pretemp.nozzletemp.txt=\"%d / %d\"" % (data.hotend, data.hotend_target))
        if data.bed != self.printer.bed or data.bed_target != self.printer.bed_target:
            self.write("pretemp.bedtemp.txt=\"%d / %d\"" % (data.bed, data.bed_target))
        if data.x_pos != self.printer.x_pos:
            self.write("premove.x_pos.val=%d" % (int)(data.x_pos * 100))
        if data.y_pos != self.printer.y_pos:
            self.write("premove.y_pos.val=%d" % (int)(data.y_pos * 100))
        if data.z_pos != self.printer.z_pos:
            self.write("premove.z_pos.val=%d" % (int)(data.z_pos * 100))
            if data.state != "printing":
                self.write("adjustzoffset.z_offset.val=%d" % (int)(data.z_pos * 1000))
        if data.z_offset != self.printer.z_offset:
            self.printer.z_offset = data.z_offset
            self.write("adjustzoffset.z_offset.val=%d" % int((data.z_offset) * 1000))

        if self.adjusting_max1:
            if data.fan != self.printer.fan:
                self.write("set.h5.val=%d" % data.fan)
                self.write("set.vent.val=%d" % data.fan)
        if data.fan > 0:
            self.write("set.va0.val=1")
        else:
            self.write("set.va0.val=0")

        if self.adjusting_max2:
            if data.light != self.printer.light:
                self.write("multiset1.led_puente.val=%d" % data.light)
                self.write("multiset1.h4.val=%d" % data.light)

            if data.neo_r != self.printer.neopixel_r:
                self.write("multiset1.h1.val=%d" % data.neo_r)
                self.write("multiset1.r1.val=%d" % data.neo_r)
            if data.neo_g != self.printer.neopixel_g:
                self.write("multiset1.h2.val=%d" % data.neo_g)
                self.write("multiset1.r2.val=%d" % data.neo_g)
            if data.neo_b != self.printer.neopixel_b:
                self.write("multiset1.h3.val=%d" % data.neo_b)
                self.write("multiset1.r3.val=%d" % data.neo_b)

        if data.light != self.printer.light:
            if data.light > 0:
                self.write("multiset1.va1.val=1")
            else:
                self.write("multiset1.va1.val=0")

        if data.light1 != self.printer.light1:
            if data.light1 > 0:
                self.write("multiset1.va2.val=1")
            else:
                self.write("multiset1.va2.val=0")


        if data.filament_sensor_enabled != self.printer.filament_sensor_enabled \
            or data.filament_detected != self.printer.filament_detected:

            if data.filament_sensor_enabled:
                self.write("set.va1.val=1")
                if not data.filament_detected and data.state in ["printing", "paused", "pausing"]:
                    self.write("nofilament.va0.val=1")
                else:
                    self.write("nofilament.va0.val=0")
            else:
                self.write("set.va1.val=0")
                self.write("nofilament.va0.val=0")


        if self.probe_mode and data.z_pos != self.printer.z_pos:
            self.write("leveldata.z_offset.val=%d" % (int)(data.z_pos * 100))

        if self.speed_adjusting == 'PrintSpeed' and data.feedrate != self.printer.feedrate:
            self.write("adjustspeed.targetspeed.val=%d" % round(data.feedrate))
        elif self.speed_adjusting == 'Flow' and data.flowrate != self.printer.flowrate:
            self.write("adjustspeed.targetspeed.val=%d" % round(data.flowrate))
        elif self.speed_adjusting == 'Fan' and data.fan != self.printer.fan:
            self.write("adjustspeed.targetspeed.val=%d" % data.fan)

        if self.adjusting_max:
            if data.max_accel != self.printer.max_accel:
                self.write("speed_settings.accel.val=%d" % data.max_accel)
            if data.minimum_cruise_ratio != self.printer.minimum_cruise_ratio:
                self.write("speed_settings.accel_to_decel.val=%d" % data.minimum_cruise_ratio)
            if data.max_velocity != self.printer.max_velocity:
                self.write("speed_settings.velocity.val=%d" % data.max_velocity)
            if data.square_corner_velocity != self.printer.square_corner_velocity:
                self.write("speed_settings.sqr_crnr_vel.val=%d" % data.square_corner_velocity)
            if data.pressure_advance != self.printer.pressure_advance:
                self.write("speed_settings.press_adv.val=%d" % int(data.pressure_advance))
        if data.state != self.printer.state:
                print("Printer state: %s" % data.state)
                if data.state == "printing":
                    self.write("restFlag1=0")
                    self.write("restFlag2=1")
                    self.write("page printpause")
                    self.write('printpause.t4.txt="Imprimiendo"')
                    if self.is_thumbnail_written == False:
                        self.callback(self.evt.THUMBNAIL, None)
                elif data.state == "paused" or data.state == "pausing":
                    #self.write("page printpause")
                    self.write("restFlag1=1")
                    if self.is_thumbnail_written == False:
                        self.callback(self.evt.THUMBNAIL, None)
                    self.write('printpause.t4.txt="Pausado"')
                elif (data.state == "cancelled"):
                    if self.bandera == 1 and data.state == "cancelled":
                        self.write('printpause.t4.txt="Cancelado"')
                        self.write("page printfinish")
                        self.is_thumbnail_written = False
                elif (data.state == "complete"):
                    if self.bandera == 1 and data.state == "complete":
                        self.write('printpause.t4.txt="Completado"')
                        self.write("page printfinish")
                        self.is_thumbnail_written = False

        if data != self.printer:
            self.printer = data

    def probe_mode_start(self):
        self.probe_mode = True
        self.z_offset_unit = 0.01
        self.write("adjustzoffset.z_offset.val=%d" % (int)(self.printer.z_pos * 1000))

    def run(self):
        while self.running:
            incomingByte = self.ser.read(1)
            if not incomingByte:
                continue
            
            if self.rx_state == RX_STATE_IDLE:
                if incomingByte[0] == FHONE:
                    self.rx_buf.extend(incomingByte)
                elif incomingByte[0] == FHTWO:
                    if len(self.rx_buf) > 0 and self.rx_buf[0] == FHONE:
                        self.rx_buf.extend(incomingByte)
                        self.rx_state = RX_STATE_READ_LEN
                    else:
                        self.rx_buf.clear()
                        print("Unexpected header received: 0x%02x ()" % incomingByte[0])
                        
                elif incomingByte[0] == 0x71:
                    self._handle_get_response()
                    
                else:
                    self.rx_buf.clear()
                    self.error_from_lcd = True
                    print("Unexpected data received: 0x%02x" % incomingByte[0])
            
            elif self.rx_state == RX_STATE_READ_LEN:
                self.rx_buf.extend(incomingByte)
                self.rx_state = RX_STATE_READ_DAT
            
            elif self.rx_state == RX_STATE_READ_DAT:
                self.rx_buf.extend(incomingByte)
                self.rx_data_cnt += 1
                msg_len = self.rx_buf[2]
                if self.rx_data_cnt >= msg_len:
                    cmd = self.rx_buf[3]
                    data = self.rx_buf[-(msg_len-1):]
                    self._handle_command(cmd, data)
                    self.rx_buf.clear()
                    self.rx_data_cnt = 0
                    self.rx_state = RX_STATE_IDLE

    def _handle_command(self, cmd, dat):
        if cmd == CMD_WRITEVAR: #0x82
            print("Write variable command received")
            print(binascii.hexlify(dat))
        elif cmd == CMD_READVAR: #0x83
            addr = dat[0]
            addr = (addr << 8) | dat[1]
            bytelen = dat[2]
            data = [32]
            for i in range (0, bytelen, 2):
                idx = int(i / 2)
                data[idx] = dat[3 + i]
                data[idx] = (data[idx] << 8) | dat[4 + i]
            self._handle_readvar(addr, data)
        elif cmd == CMD_CONSOLE: #0x42
            addr = dat[0]
            addr = (addr << 8) | dat[1]
            data = dat[3:] # Remove addr and len
            self._handle_readvar(addr, data)
        else:
            print("Command not reqognised: %d" % cmd)
            print(binascii.hexlify(dat))

    def _handle_readvar(self, addr, data):
        if addr in self.addr_func_map:
            # Call function corresponding with addr
            if (self.addr_func_map[addr].__name__ == "_BedLevelFun" and data[0] == 0x0a):
                pass ## Avoid to spam the log file while printing
            else:
                print("%s: len: %d data[0]: %x" % (self.addr_func_map[addr].__name__, len(data), data[0]))
            self.addr_func_map[addr](data)
        else:
            print("_handle_readvar: addr %x not recognised" % addr)


    def _handle_get_response(self):
        response_bytes = self.ser.read(4)
        terminator = self.ser.read(3)

        if len(response_bytes) == 4:
            val = int.from_bytes(response_bytes, 'little', signed=True)
            self.last_read_value = val
        else:
            print("[ERROR] Respuesta 'get' incompleta desde el LCD.")
            self.last_read_value = None

        if self.waiting_for_value:
            self.waiting_for_value = False

    def _Console(self, data):
        try:
            text = data.decode('utf-8', errors='replace')
            print(text)
        except Exception as e:
            print(f"[ERROR _Console] Error decodificando datos: {e}")
            print(f"[ERROR _Console] Datos crudos: {data}")

        # Depuración adicional para identificar el origen del 0xA5
        hex_data = ' '.join(f'{b:02X}' for b in data)
        print(f"[DEBUG _Console] Longitud: {len(data)}  Bytes: {hex_data}")

        try:
            if b'SET_LED' in data:
                text = data.decode('utf-8', errors='replace')
                print(f"[GCODE DETECTADO] {text}")
        except Exception as e:
            print(f"[ERROR _Console Extra] {e}")


    def _MainPage(self, data):
        if data[0] == 1: # Print
            # Request files
            files = self.callback(self.evt.FILES)
            self.files = files
            if (files):
                i = 0
                for file in files:
                    print(file)
                    page_num = ((i / 5) + 1)
                    self.write("file%d.t%d.txt=\"%s\"" % (page_num, i, file))
                    i += 1
                self.write("page file1")
            else:
                self.files = False
                # Clear old files from LCD
                for i in range(0, MaxFileNumber):
                        page_num = ((i / 5) + 1)
                        self.write("file%d.t%d.txt=\"\"" % (page_num, i))
                self.write("page nosdcard")

        elif data[0] == 2: # Abort print
            print("Abort print not supported") #TODO:
        else:
            print("_MainPage: %d not supported" % data[0])
    
    def _Adjustment(self, data):
        if data[0] == 0x01: # Filament tab
            self.write("pretemp.targettemp.val=%d" % self.printer.hotend_target)
            self.write("pretemp.va0.val=1")
            self.write("pretemp.va1.val=3") #Setting default to 10
            self.adjusting = 'Hotend'
            self.temp_unit = 10
            self.move_unit = 1
        elif data[0] == 0x05:
            print("Filament tab")
            self.speed_adjusting = None
            self.write("page pretemp")
        elif data[0] == 0x06: # Speed tab
            print("Speed tab")
            self.speed_adjusting = 'PrintSpeed'
            self.write("adjustspeed.targetspeed.val=%d" % self.printer.feedrate)
            self.write("page adjustspeed")
        elif data[0] == 0x07: # Adjust tab
            print("Adjust tab")
            self.z_offset_unit = 0.01
            self.speed_adjusting = None
            self.write("adjustzoffset.zoffset_value.val=2")
            print(self.printer.z_offset)
            self.write("adjustzoffset.z_offset.val=%d" % (int)(self.printer.z_pos * 1000))
            self.write("page adjustzoffset")
        elif data[0] == 0x08: #
            self.printer.feedrate = 100
            self.write("adjustspeed.targetspeed.val=%d" % 100)
            self.callback(self.evt.PRINT_SPEED, self.printer.feedrate)
        elif data[0] == 0x09:
            self.printer.flowrate = 100
            self.write("adjustspeed.targetspeed.val=%d" % 100)
            self.callback(self.evt.FLOW, self.printer.flowrate)
        elif data[0] == 0x0a:
            self.printer.fan = 100
            self.write("adjustspeed.targetspeed.val=%d" % 100)
            self.callback(self.evt.FAN, self.printer.fan)
        else:
            print("_Adjustment: %d not supported" % data[0])

    def _PrintSpeed(self, data):
        print("_PrintSpeed: %d not supported" % data[0])

    def _StopPrint(self, data):
        if data[0] == 0x01 or data[0] == 0xf1:
            self.callback(self.evt.PRINT_STOP)
            self.write("page resumeconfirm1")

        else:
            print("_StopPrint: %d not supported" % data[0])

    def _PausePrint(self, data):
        if data[0] == 0x01:
            if self.printer.state == "printing":
                self.write("page pauseconfirm")
        elif data[0] == 0xF1:
            self.callback(self.evt.PRINT_PAUSE)



    def _ResumePrint(self, data):
        if data[0] == 0x01:
            if self.printer.state == "paused" or self.printer.state == "pausing":
                self.callback(self.evt.PRINT_RESUME)
            self.write("page printpause")
        else:
            print("_ResumePrint: %d not supported" % data[0])

    def _ZOffset(self, data):
        print("_ZOffset: %d not supported" % data[0])

    def _TempScreen(self, data):
        if data[0] == 0x01: # Hotend
            self.write("pretemp.targettemp.val=%d" % self.printer.hotend_target)
            self.adjusting = 'Hotend'
        elif data[0] == 0x03: # Heatbed
            self.write("pretemp.targettemp.val=%d" % self.printer.bed_target)
            self.adjusting = 'Heatbed'
        elif data[0] == 0x04: #
            pass
        elif data[0] == 0x05: # Move 0.1mm / 1C / 1%
            self.temp_unit = 1
            self.speed_unit = 1
            self.move_unit = 0.1
            self.accel_unit = 10
        elif data[0] == 0x06: # Move 1mm / 5C / 5%
            self.temp_unit = 5
            self.speed_unit = 5
            self.move_unit = 1
            self.accel_unit = 50
        elif data[0] == 0x07: # Move 10mm / 10C /10%
            self.temp_unit = 10
            self.speed_unit = 10
            self.move_unit = 10
            self.accel_unit = 100
        elif data[0] == 0x02: # Move 100mm / 100c /100%
            self.temp_unit = 100
            self.speed_unit = 100
            self.move_unit = 100
            self.accel_unit = 1000
        elif data[0] == 0x08: # + temp
            if self.adjusting == 'Hotend':
                self.printer.hotend_target += self.temp_unit
                self.write("pretemp.targettemp.val=%d" % self.printer.hotend_target)
                self.callback(self.evt.NOZZLE, self.printer.hotend_target)
            elif self.adjusting == 'Heatbed':
                self.printer.bed_target += self.temp_unit
                self.write("pretemp.targettemp.val=%d" % self.printer.bed_target)
                self.callback(self.evt.BED, self.printer.bed_target)

        elif data[0] == 0x09: # - temp
            if self.adjusting == 'Hotend':
                self.printer.hotend_target -= self.temp_unit
                self.write("pretemp.targettemp.val=%d" % self.printer.hotend_target)
                self.callback(self.evt.NOZZLE, self.printer.hotend_target)
            elif self.adjusting == 'Heatbed':
                self.printer.bed_target -= self.temp_unit
                self.write("pretemp.targettemp.val=%d" % self.printer.bed_target)
                self.callback(self.evt.BED, self.printer.bed_target)
        elif data[0] == 0x0a: # Print
            self.write("adjustspeed.targetspeed.val=%d" % self.printer.feedrate)
            self.speed_adjusting = 'PrintSpeed'
        elif data[0] == 0x0b: # Flow
            self.write("adjustspeed.targetspeed.val=%d" % self.printer.flowrate)
            self.speed_adjusting = 'Flow'
        elif data[0] == 0x0c: # Fan
            self.write("adjustspeed.targetspeed.val=%d" % self.printer.fan)
            self.speed_adjusting = 'Fan'
        elif data[0] == 0x0d or data[0] == 0x0e: # Adjust speed
            unit = self.speed_unit
            if data[0] == 0x0e:
                unit = -self.speed_unit
            if self.speed_adjusting == 'PrintSpeed':
                self.printer.feedrate = max(1, round(self.printer.feedrate + unit))
                self.write("adjustspeed.targetspeed.val=%d" % self.printer.feedrate)
                self.callback(self.evt.PRINT_SPEED, self.printer.feedrate)
            elif self.speed_adjusting == 'Flow':
                self.printer.flowrate = max(1, round(self.printer.flowrate + unit))
                self.write("adjustspeed.targetspeed.val=%d" % self.printer.flowrate)
                self.callback(self.evt.FLOW, self.printer.flowrate)
            elif self.speed_adjusting == 'Fan':
                self.printer.fan = max(0, min(100, self.printer.fan + unit))
                self.write("adjustspeed.targetspeed.val=%d" % self.printer.fan)
                self.callback(self.evt.FAN, self.printer.fan)
            else:
                print("self.speed_adjusting not recognised %s" % self.speed_adjusting)
        elif data[0] == 0x42: # Accel/Speed advanced
            self.speed_unit = 10
            self.accel_unit = 100
            self.adjusting_max = True
            self.write("speed_settings.accel.val=%d" % self.printer.max_accel)
            self.write("speed_settings.accel_to_decel.val=%d" % self.printer.minimum_cruise_ratio)
            self.write("speed_settings.velocity.val=%d" % self.printer.max_velocity)
            self.write("speed_settings.sqr_crnr_vel.val=%d" % self.printer.square_corner_velocity)
            self.write("speed_settings.press_adv.val=%d" % int(self.printer.pressure_advance))
        elif data[0] == 0x43: # Max acceleration set
            self.adjusting_max = False

        elif data[0] == 0x11 or data[0] == 0x15: #Accel decrease / increase
            unit = self.accel_unit
            if data[0] == 0x11:
                unit = -self.accel_unit
            new_accel = self.printer.max_accel + unit
            self.write("speed_settings.accel.val=%d" % new_accel)
            self.callback(self.evt.ACCEL, new_accel)
            self.printer.max_accel = new_accel

        elif data[0] == 0x12 or data[0] == 0x16: #minimum_cruise_ratio decrease / increase
            unit = self.accel_unit/10
            if data[0] == 0x12:
                unit = -self.accel_unit/10
            new_accel = self.printer.minimum_cruise_ratio + unit
            self.write("speed_settings.accel_to_decel.val=%d" % new_accel)
            self.callback(self.evt.CONSOLE, "SET_VELOCITY_LIMIT MINIMUM_CRUISE_RATIO=%.2f" %  (new_accel / 100.0))
            self.printer.minimum_cruise_ratio = new_accel

        elif data[0] == 0x13 or data[0] == 0x17: #Velocity decrease / increase
            unit = self.speed_unit
            if data[0] == 0x13:
                unit = -self.speed_unit
            new_velocity = self.printer.max_velocity + unit
            self.write("speed_settings.velocity.val=%d" % new_velocity)
            self.callback(self.evt.VELOCITY, new_velocity)
            self.printer.max_velocity = new_velocity

        elif data[0] == 0x14 or data[0] == 0x18: #Square Corner Velozity decrease / increase
            unit = self.speed_unit
            if data[0] == 0x14:
                unit = -self.speed_unit
            new_velocity = self.printer.square_corner_velocity + unit
            self.write("speed_settings.sqr_crnr_vel.val=%d" % int(new_velocity))
            self.callback(self.evt.SQUARE_CORNER_VELOCITY, (new_velocity / 10))
            self.printer.square_corner_velocity = new_velocity

        elif data[0] == 0x19 or data[0] == 0x1a:
            unit = self.speed_unit
            if data[0] == 0x1a:
                unit = -self.speed_unit
            new_velocity = self.printer.pressure_advance + unit
            self.write("speed_settings.press_adv.val=%d" % int(new_velocity))
            self.callback(self.evt.PRESSURE_ADVANCE, (new_velocity /1000))
            self.printer.pressure_advance = new_velocity


        else:
            print("_TempScreen: Not recognised %d" % data[0])

    def _CoolScreen(self, data):
        if data[0] == 0x01: #Turn off nozzle
            if self.printer.state == "printing":
                # Ignore
                self.write("pretemp.targettemp.val=%d" % self.printer.hotend_target)
            else:
                self.callback(self.evt.NOZZLE, 0)
        elif data[0] == 0x02: #Turn off bed
            self.callback(self.evt.BED, 0)
        elif data[0] == 0x09: #Preheat PLA
            self.callback(self.evt.NOZZLE, self.preset_temp[PLA])
            self.callback(self.evt.BED, self.preset_bed_temp[PLA])
            self.write("pretemp.nozzle.txt=\"%d\"" % self.preset_temp[PLA])
            self.write("pretemp.bed.txt=\"%d\"" % self.preset_bed_temp[PLA])
        elif data[0] == 0x0a: #Preheat ABS
            self.callback(self.evt.NOZZLE, self.preset_temp[ABS])
            self.callback(self.evt.BED, self.preset_bed_temp[ABS])
            self.write("pretemp.nozzle.txt=\"%d\"" % self.preset_temp[ABS])
            self.write("pretemp.bed.txt=\"%d\"" % self.preset_bed_temp[ABS])
        elif data[0] == 0x0b: #Preheat PETG
            self.callback(self.evt.NOZZLE, self.preset_temp[PETG])
            self.callback(self.evt.BED, self.preset_bed_temp[PETG])
            self.write("pretemp.nozzle.txt=\"%d\"" % self.preset_temp[PETG])
            self.write("pretemp.bed.txt=\"%d\"" % self.preset_bed_temp[PETG])
        elif data[0] == 0x0c: #Preheat TPU
            self.callback(self.evt.NOZZLE, self.preset_temp[TPU])
            self.callback(self.evt.BED, self.preset_bed_temp[TPU])
            self.write("pretemp.nozzle.txt=\"%d\"" % self.preset_temp[TPU])
            self.write("pretemp.bed.txt=\"%d\"" % self.preset_bed_temp[TPU])
        elif data[0] == 0x0d: #Preheat PLA setting
            self.preset_index = PLA
            self.write("tempsetvalue.nozzletemp.val=%d" % self.preset_temp[PLA])
            self.write("tempsetvalue.bedtemp.val=%d" % self.preset_bed_temp[PLA])
            self.write("page tempsetvalue")
        elif data[0] == 0x0e: #Preheat ABS setting
            self.preset_index = ABS
            self.write("tempsetvalue.nozzletemp.val=%d" % self.preset_temp[ABS])
            self.write("tempsetvalue.bedtemp.val=%d" % self.preset_bed_temp[ABS])
            self.write("page tempsetvalue")
        elif data[0] == 0x0f: #Preheat PETG setting
            self.preset_index = PETG
            self.write("tempsetvalue.nozzletemp.val=%d" % self.preset_temp[PETG])
            self.write("tempsetvalue.bedtemp.val=%d" % self.preset_bed_temp[PETG])
            self.write("page tempsetvalue")
        elif data[0] == 0x10: #Preheat TPU setting
            self.preset_index = TPU
            self.write("tempsetvalue.nozzletemp.val=%d" % self.preset_temp[TPU])
            self.write("tempsetvalue.bedtemp.val=%d" % self.preset_bed_temp[TPU])
            self.write("page tempsetvalue")
        elif data[0] == 0x11: # Level
            self.preset_index = PROBE
            self.write("tempsetvalue.nozzletemp.val=%d" % self.preset_temp[PROBE])
            self.write("tempsetvalue.bedtemp.val=%d" % self.preset_bed_temp[PROBE])
            self.write("page tempsetvalue")
        else:
            print("_CoolScreen: Not recognised %d" % data[0])

    def _Heater0TempEnter(self, data):
        temp = ((data[0] & 0x00FF) << 8) | ((data[0] & 0xFF00) >> 8)
        print("Set nozzle temp: %d" % temp)
        self.callback(self.evt.NOZZLE, temp)

    def _Heater1TempEnter(self, data):
        print("_Heater1TempEnter: %d not supported" % data[0])

    def _HotBedTempEnter(self, data):
        temp = ((data[0] & 0x00FF) << 8) | ((data[0] & 0xFF00) >> 8)
        self.callback(self.evt.BED, temp)

    def _SettingScreen(self, data):
        if data[0] == 0x01:
            self.callback(self.evt.PROBE)
        elif data[0] == 0x02:
            self.write("adjustzoffset.z_offset.val=%d" % int(self.printer.z_pos * 1000))
        elif data [0] == 0x03:
            self.write("adjustzoffset.z_offset.val=%d" % int((self.printer.z_offset) * 1000))
        elif data[0] == 0x06: # Motor release
            self.callback(self.evt.MOTOR_OFF)
        elif data[0] == 0x07: # Fan Control
            if self.printer.fan > 0:
                self.callback(self.evt.FAN, 0)
            else:
                self.callback(self.evt.FAN, 100)

        elif data[0] == 0x08:  # Filament Sensor toggle
            new_state = 0 if self.printer.filament_sensor_enabled else 1
            self.callback(self.evt.FILAMENT_SENSOR, new_state)



        elif data[0] == 0x09: #
            self.write("page pretemp")
            self.write("pretemp.nozzle.txt=\"%d\"" % self.printer.hotend_target)
            self.write("pretemp.bed.txt=\"%d\"" % self.printer.bed_target)
        elif data[0] == 0x0a:
            self.write("page prefilament")
            self.write("prefilament.filamentlength.txt=\"%d\"" % self.load_len)
            self.write("prefilament.filamentspeed.txt=\"%d\"" % self.feedrate_e)
        elif data[0] == 0x0b:
            self.write("page set")

        else:
            print("_SettingScreen: Not recognised %d" % data[0])

        return

    def _SettingBack(self, data):
        if data[0] == 0x01:
            if self.probe_mode:
                self.probe_mode = False
                self.callback(self.evt.PROBE_BACK)
        else:
            print("_SettingScreen: Not recognised %d" % data[0])

    def _BedLevelFun(self, data):
        if data[0] == 0x01:
            self.callback(self.evt.SCREWS_TILT, None)

        elif data[0] == 0x02 or data[0] == 0x03:  # Z Offset Up / Down
            unit = self.z_offset_unit
            if data[0] == 0x03:
                unit = -self.z_offset_unit
            if self.printer.state == "printing":
                self.callback(self.evt.BABYSTEP, unit)
                self.write("adjustzoffset.z_offset.val=%d" % int((self.printer.z_offset) * 1000))
            else:
                self.callback(self.evt.PROBE, unit)
                self.write("adjustzoffset.z_offset.val=%d" % int(self.printer.z_pos * 1000))

        elif data[0] == 0x04:
            self.z_offset_unit = 0.01
        elif data[0] == 0x05:
            self.z_offset_unit = 0.05
        elif data[0] == 0x06:
            self.z_offset_unit = 0.1
        elif data[0] == 0x0d:
            self.z_offset_unit = 1

        elif data[0] == 0x07:
            self.callback(self.evt.LIGHT1)

        elif data[0] == 0x08:
            if self.printer.light > 0:
                self.callback(self.evt.LIGHT, 0)
            else:
                self.callback(self.evt.LIGHT, 100)

        elif data[0] == 0x0a:
            self.write("printpause.printspeed.txt=\"%d\"" % self.printer.feedrate)
            self.write("printpause.fanspeed.val=%d" % self.printer.fan)
            self.write("printpause.duration.txt=\"%s\"" % self.printer.duration)
            self.write("printpause.printtime.txt=\"%d h %d min\"" % (self.printer.remaining/3600,(self.printer.remaining % 3600)/60))
            self.write("printpause.printprocess.val=%d" % self.printer.percent)
            self.write("printpause.printvalue.txt=\"%d\"" % self.printer.percent)
            self.write("printpause.layer.txt=\"%d / %d\"" % (self.printer.current_layer, self.printer.total_layer))

        elif data[0] == 0x16:
            self.write("printpause.t0.txt=\"%s\"" % self.printer.file_name)


        else:
            print("_BedLevelFun: Data not recognised %d" % data[0])

    def _AxisPageSelect(self, data):
        if data[0] == 0x04: #Home all
            self.callback(self.evt.HOME, 'X Y Z')
        elif data[0] == 0x05: #Home X
            self.callback(self.evt.HOME, 'X')
        elif data[0] == 0x06: #Home Y
            self.callback(self.evt.HOME, 'Y')
        elif data[0] == 0x07: #Home Z
            self.callback(self.evt.HOME, 'Z')
        else:
            print("_AxisPageSelect: Data not recognised %d" % data[0])

    def _Xaxismove(self, data):
        if data[0] == 0x01: # X+
            self.callback(self.evt.MOVE_X, self.move_unit)
        elif data[0] == 0x02: # X-
            self.callback(self.evt.MOVE_X, -self.move_unit)
        else:
            print("_Xaxismove: Data not recognised %d" % data[0])

    def _Yaxismove(self, data):
        if data[0] == 0x01: # Y+
            self.callback(self.evt.MOVE_Y, self.move_unit)
        elif data[0] == 0x02: # Y-
            self.callback(self.evt.MOVE_Y, -self.move_unit)
        else:
            print("_Yaxismove: Data not recognised %d" % data[0])

    def _Zaxismove(self, data):
        if data[0] == 0x01: # Z+
            self.callback(self.evt.MOVE_Z, self.move_unit)
        elif data[0] == 0x02: # Z-
            self.callback(self.evt.MOVE_Z, -self.move_unit)
        else:
            print("_Zaxismove: Data not recognised %d" % data[0])

    def _SelectExtruder(self, data):
        print("_SelectExtruder: Not recognised %d" % data[0])

    def _Heater0LoadEnter(self, data):
        load_len = ((data[0] & 0x00FF) << 8) | ((data[0] & 0xFF00) >> 8)
        self.load_len = load_len
        print(load_len)

    def _Heater1LoadEnter(self, data):
        feedrate_e = ((data[0] & 0x00FF) << 8) | ((data[0] & 0xFF00) >> 8)
        self.feedrate_e = feedrate_e
        print(feedrate_e)

    def _FilamentLoad(self, data):
        if data[0] == 0x07:
           if self.printer.state == 'printing':
               self.write("page warn_move")
           else:
               self.write("page premove")

        elif data[0] in {0x01, 0x02, 0x05, 0x06}:
           if self.printer.hotend < self.printer.extrude_mintemp:
               self.write("page warn2_filament")
           elif self.printer.state == 'printing':
               self.write("page warn1_filament")
           else:
               if data[0] == 0x01:
                   self.callback(self.evt.MOVE_E, [-self.load_len, self.feedrate_e])
               elif data[0] == 0x02:
                   self.callback(self.evt.MOVE_E, [self.load_len, self.feedrate_e])
               elif data[0] == 0x05:
                   self.callback(self.evt.CONSOLE, "UNLOAD_FILAMENT")
               elif data[0] == 0x06:
                   self.callback(self.evt.CONSOLE, "LOAD_FILAMENT")

        else:
            print("_FilamentLoad: Not recognised %d" % data[0])

    def _ComandosKlipper(self, data):
        if data[0] == 0x01:
            self.callback(self.evt.CONSOLE, "SAVE_CONFIG")
        elif data[0] == 0x02:
            self.callback(self.evt.CONSOLE, "RESTART")
        elif data[0] == 0x03:
            self.callback(self.evt.CONSOLE, "FIRMWARE_RESTART")
        elif data[0] == 0x04:
            self.callback(self.evt.EMERGENCY_STOP, None)
        elif data[0] == 0x05:
            self.callback(self.evt.REBOOT_PI, None)
        elif data[0] == 0x06:
            self.callback(self.evt.RESTART_LCD, None)
        elif data[0] == 0x07:
            self.callback(self.evt.SHUTDOWN_PI, None)
        elif data[0] == 0x08:
            self.callback(self.evt.STOP_LCD, None)
        elif data[0] == 0x09:
            self.callback(self.evt.CONSOLE, "BED_MESH_CALIBRATE")
        elif data[0] == 0x0a:
            self.callback(self.evt.CONSOLE, "ACCEPT")
        elif data[0] == 0x0b:
            self.callback(self.evt.CONSOLE, "ABORT")
        elif data[0] == 0x0c:
            self.callback(self.evt.CONSOLE, "SET_GCODE_OFFSET Z=0 MOVE=1")
        elif data[0] == 0x0d:
            self.callback(self.evt.CONSOLE, "Z_OFFSET_APPLY_PROBE")
        elif data[0] == 0x0e:
            self.callback(self.evt.CONSOLE, "BED_MESH_CLEAR")

        else:
            print("_ComandosKlipper: Not recognised %d" % data[0])

    def _FilamentCheck(self, data):
        if data[0] == 0x01:
            self.bandera = 1
        elif data[0] == 0x02:
            self.bandera = 0

        else:
            print("_FilamentCheck: Not recognised %d" % data[0])

    def _PowerContinuePrint(self, data):
        print("_PowerContinuePrint: Not recognised", data)

    def _PrintSelectMode(self, data):
        print("_LedSlider: Not recognised", data)


    def _XhotendOffset(self, data):
        print("_XhotendOffset: Not recognised %d" % data[0])

    def _YhotendOffset(self, data):
        print("_YhotendOffset: Not recognised %d" % data[0])

    def _ZhotendOffset(self, data):
        print("_ZhotendOffset: Not recognised %d" % data[0])

    def _StoreMemory(self, data):
        print("_StoreMemory: Not recognised %d" % data[0])

    def _PrintFile(self, data):
        if data[0] == 0x01:
            self.write("file%d.t%d.pco=65504" % ((self.selected_file / 5) + 1, self.selected_file))
            self.write("printpause.printprocess.val=%d" % self.printer.percent)
            self.write("printpause.printvalue.txt=\"%d\"" % self.printer.percent)
            #self.write("printpause.printvalue.txt=\"0\"")
            #self.write("printpause.printprocess.val=0")
            self.write("page printpause")
            self.write("restFlag2=1")
            self.callback(self.evt.PRINT_START, self.selected_file)

        elif data[0] == 0x0A:
            if self.askprint:
                self.askprint = False
            else:
                self.write("page main")
        else:
            print("_PrintFile: Not recognised %d" % data[0])

    def _SelectFile(self, data):
        print(self.files)
        if self.files and data[0] <= len(self.files):
            self.selected_file = (data[0] - 1)
            self.write("askprint.t0.txt=\"%s\"" % self.files[self.selected_file])
            self.write("printpause.t0.txt=\"%s\"" % self.files[self.selected_file])
            self.write("askprint.cp0.close()")
            self.write("askprint.cp0.aph=0")
            self.write("page askprint")
            self.callback(self.evt.THUMBNAIL)
            self.askprint = True
        else:
            print("_SelectFile: Data not recognised %d" % data[0])


    def _ChangePage(self, data):
        print("_ChangePage: Not recognised %d" % data[0])

    def _SetPreNozzleTemp(self, data):
        material = self.preset_index
        if data[0] == 0x01:
            self.preset_temp[material] += self.temp_unit
        elif data[0] == 0x02:
            self.preset_temp[material] -= self.temp_unit
        self.write("tempsetvalue.nozzletemp.val=%d" % self.preset_temp[material])

    def _SetPreBedTemp(self, data):
        material = self.preset_index
        if data[0] == 0x01:
            self.preset_bed_temp[material] += self.temp_unit
        elif data[0] == 0x02:
            self.preset_bed_temp[material] -= self.temp_unit
        material = self.preset_index
        self.write("tempsetvalue.bedtemp.val=%d" % self.preset_bed_temp[material])

    def _HardwareTest(self, data):
        if data[0] == 0x01:
            subprocess.Popen(["python3", "/home/pi/KlipperLCD/firmw_update.py"])
        elif data[0] == 0x02:
            subprocess.Popen(["systemctl", "start", "firmw.service"])

        elif data[0] == 0x0f:
            pass
        else:
            print ("_HardwareTest: Not implemented: 0x%x" % data[0])

    def send_wait_variable(self):
        self.write("wait.va1.val=1")

    def _Err_Control(self, data):
        if data[0] == 0x01:
            self.adjusting_max1 = True
            self.write("set.h5.val=%d" % self.printer.fan)
            self.write("set.vent.val=%d" % self.printer.fan)
        elif data[0] == 0x02:
            self.adjusting_max1 = False
        elif data[0] == 0x03:
            self.adjusting_max2 = True
            self.write("multiset1.led_puente.val=%d" % self.printer.light)
            self.write("multiset1.h4.val=%d" % self.printer.light)
            self.write("multiset1.h1.val=%d" % self.printer.neo_r)
            self.write("multiset1.r1.val=%d" % self.printer.neo_r)
            self.write("multiset1.h2.val=%d" % self.printer.neo_g)
            self.write("multiset1.r2.val=%d" % self.printer.neo_g)
            self.write("multiset1.h3.val=%d" % self.printer.neo_b)
            self.write("multiset1.r3.val=%d" % self.printer.neo_b)

        elif data[0] == 0x04:
            self.adjusting_max2 = False

        else:
            print("_Err_Control: Not recognised %d" % data[0])

    def show_screws_data(self, screws):
        self.write("page screw_level")
        for idx, (name, sign, adjust, z, is_base) in enumerate(screws, start=1):
            self.write(f"screw{idx}_name.txt=\"{name}\"")
            self.write(f"screw{idx}_dir.txt=\"{sign}\"")
            self.write(f"screw{idx}_time.txt=\"{adjust}\"")
            if is_base:
                self.write(f"screw{idx}_base.txt=\"BASE\"")
            self.write("screw_level.va0.val=1")

    def show_bed_mesh(self, mesh):
        layouts = {
            3: [
                [ 8, 7, 6],
                [ 3, 4, 5],
                [ 2, 1, 0],
            ],
            4: [
                [12,13,14,15],
                [11,10, 9, 8],
                [ 4, 5, 6, 7],
                [ 3, 2, 1, 0],
            ],
            5: [
                [24,23,22,21,20],
                [15,16,17,18,19],
                [14,13,12,11,10],
                [ 5, 6, 7, 8, 9],
                [ 4, 3, 2, 1, 0],
            ],
            6: [
                [30,31,32,33,34,35],
                [29,28,27,26,25,24],
                [18,19,20,21,22,23],
                [17,16,15,14,13,12],
                [ 6, 7, 8, 9,10,11],
                [ 5, 4, 3, 2, 1, 0],
            ],
            7: [
                [42,43,44,45,46,47,48],
                [41,40,39,38,37,36,35],
                [28,29,30,31,32,33,34],
                [27,26,25,24,23,22,21],
                [14,15,16,17,18,19,20],
                [13,12,11,10, 9, 8, 7],
                [ 0, 1, 2, 3, 4, 5, 6],
            ],
            8: [
                [56,57,58,59,60,61,62,63],
                [55,54,53,52,51,50,49,48],
                [40,41,42,43,44,45,46,47],
                [39,38,37,36,35,34,33,32],
                [24,25,26,27,28,29,30,31],
                [23,22,21,20,19,18,17,16],
                [ 8, 9,10,11,12,13,14,15],
                [ 7, 6, 5, 4, 3, 2, 1, 0],
            ],
        }

        ny = len(mesh)
        nx = len(mesh[0]) if ny > 0 else 0

        if nx not in layouts or ny != nx:
            self.write("autohome.va0.val=2")
            return

        page_map = {
            3: "leveldata_9",
            4: "leveldata_16",
            5: "leveldata_25",
            6: "leveldata_36",
            7: "leveldata_49",
            8: "leveldata_64",
        }
        page_val = {
            3: "autohome.va0.val=3",
            4: "autohome.va0.val=4",
            5: "autohome.va0.val=5",
            6: "autohome.va0.val=6",
            7: "autohome.va0.val=7",
            8: "autohome.va0.val=8",
        }
        page = page_map[nx]
        page1 = page_val[nx]
        self.write(f"{page1}")

        layout = layouts[nx]

        for y in range(ny):
            for x in range(nx):
                val = mesh[ny - 1 - y][x]
                lcd_idx = layout[y][x]
                try:
                    val_int = int(round(val * 100))  # convertir -0.05 → -5
                    self.write(f"{page}.x{lcd_idx}.val={val_int}")
                except Exception:
                    pass
