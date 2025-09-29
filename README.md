# KlipperLCD (for Artillery X3 plus/Pro LCD screen)
Want to run Klipper on your Artillery x3 Plus/Pro? And still want to be able to use your Artillery x3 Plus/Pro LCD touch screen?

# [GHITHUB](https://github.com/Vampiro1/LCD_Artillery_x3)

Take a look at this python service for the Artillery x3 Plus/Pro LCD! Running together with Klipper3d and Moonraker!

## Look and feel
<p float="left">
    <img src="img/boot_screen.PNG" height="400">
    <img src="img/main_screen.PNG" height="400">
    <img src="img/about_screen.PNG" height="400">
</p>

## Whats needed?
* A Artillery x3 Plus/Pro with LCD screen.
* A Raspberry Pi or similar SBC to run Klipper. I suggest using the [Klipper Installation And Update Helper (KIAUH)](https://github.com/dw-0/kiauh) to setup and install Klipper, Moonraker and the web user interface of choice ([Fluidd](https://docs.fluidd.xyz/)/[Mainsail](https://docs.mainsail.xyz/)).
* Some re-wiring of the LCD screen to connect it to one of the UARTs availible on your Raspberry Pi / SBC or through a USB to UART converter.
* Then you can follow this guide to enable your Neptune 3 Pro touch screen!

## Wire the LCD
When wiring your screen, you can either wire it directly to one of your Raspberry Pi / SBC availible UARTs or you can wire it through a USB to UART converter. Both options are described below, pick the option that suits your needs.

### To a Raspberry Pi UART
1. Remove the back-cover of the LCD by unscrewing the four screws.

2. Connect the LCD to the Raspberry Pi UART according to the table below:

    | Raspberry Pi  | LCD               |
    | ------------- | ----------------- |
    | Pin 4 (5V)    | 5V  (Black wire)  |
    | Pin 6 (GND)   | GND (Red wire)    |
    | GPIO 14 (TXD) | RX  (Green wire)  |
    | GPIO 15 (RXD) | TX (Yellow wire)  |

    <p float="left">
        <img src="img/rpi_conn.png" height="400">
        <img src="img/LCD_conn.png" height="400">
    </p>

### USB to UART Converter
Quite simple, just remember to cross RX and TX on the LCD and the USB/UART HW.
| USB <-> UART HW | LCD               |
| --------------- | ----------------- |
| 5V              | 5V  (Black wire)  |
| GND             | GND (Red wire)    |
| TXD             | RX  (Green wire)  |
| RXD             | TX (Yellow wire)  |

<p float="left">
    <img src="img/USB_conn.png" height="400">
    <img src="img/LCD_conn.png" height="400">
</p>

## Update the LCD screen firmware
1. Copy the LCD screen firmware from here https://github.com/Vampiro1/LCD_Artillery_x3/releases/download/firmware/LCD.tft to the root of a FAT32 formatted micro-SD card.
2. Make sure the LCD screen is powered off.
3. Insert the micro-SD card into the LCD screens SD card holder. Back-cover needs to be removed.
4. Power on the LCD screen and wait for screen to say `Update Successed!`

## Enable the UART
> **_Note_**: You can safely skip this section if you wired the display through a USB to UART converter
### [Disable Linux serial console](https://www.raspberrypi.org/documentation/configuration/uart.md)
  By default, the primary UART is assigned to the Linux console. If you wish to use the primary UART for other purposes, you must reconfigure Raspberry Pi OS. This can be done by using raspi-config:

  * Start raspi-config: `sudo raspi-config.`
  * Select option 3 - Interface Options.
  * Select option P6 - Serial Port.
  * At the prompt Would you like a login shell to be accessible over serial? answer 'No'
  * At the prompt Would you like the serial port hardware to be enabled? answer 'Yes'
  * Exit raspi-config and reboot the Pi for changes to take effect.
  
  For full instructions on how to use Device Tree overlays see [this page](https://www.raspberrypi.org/documentation/configuration/device-tree.md). 
  
  In brief, add a line to the `/boot/config.txt` file to apply a Device Tree overlay.
    
    dtoverlay=disable-bt

## Run the KlipperLCD service
* SSH into your Raspberry Pi

### Klipper socket API
* Make sure Klipper's API socket is enabled by reading the Klipper arguments.

    Command:

        cat ~/printer_data/systemd/klipper.env

    Response:

        KLIPPER_ARGS="/home/pi/klipper/klippy/klippy.py /home/pi/printer_data/config/printer.cfg -I /home/pi/printer_data/comms/klippy.serial -l /home/pi/printer_data/logs/klippy.log -a /home/pi/printer_data/comms/klippy.sock"
    
    The KLIPPER_ARGS should include `-a /home/pi/printer_data/comms/klippy.sock`. If not add it to the klipper.env file!

### Install service
    chmod +x install.sh
    ./install.sh


## Console
The console is enabled by default and can be accessed by clicking center top of the main screen or by clicking in the designated area while printing.

The console enables sending commands and will display all gcode responses and information from Klipper normally found in the console tab in Mainsail or Fluidd.

<p float="left">
    <img src="img/console.PNG" height="400">
    <img src="img/console_key.PNG" height="400">
    <img src="img/console_num.PNG" height="400">
</p>

## Thumbnails
KlipperLCD also supports thumbnails!
set your slicer to 300x300

Follow this guide to enable thumbnails in your slicer: https://klipperscreen.readthedocs.io/en/latest/Thumbnails/

<p float="left">
    <img src="img/thumb1.png" height="400">
    <img src="img/thumb2.png" height="400">
</p>

### Uninstall service
    chmod +x uninstall.sh
    ./uninstall.sh
