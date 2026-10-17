# M-VAVE SMK-37 Pro: full flash backup

**Private.** `smk37-dump.bin` holds data unique to this unit: its factory
calibration, Bluetooth data, settings and presets. Do not publish it.

## The dump

| | |
| --- | --- |
| File | `smk37-dump.bin`, 1,048,576 bytes (the whole flash, 0x00000-0xFFFFF) |
| SHA-256 | `5f768da118d141450fcddb51ee21c4352249175826ff0a14cd2a504d55c80d0e` (also in `SHA256SUMS`) |
| Taken | 2026-10-13, stock firmware, nothing installed or changed before |
| Device | M-VAVE SMK-37 Pro, JieLi AC791N (WL82 series), chip key 0x980F |
| Flash | 1 MiB SPI NOR, JEDEC ID 0xEB6014 (the FM-1 tested earlier: 0x856014) |

Checked:

- read twice; both reads identical;
- `trimdat` (the calibration record's marker) at 0xC1224;
- the flash header and the app file table decode; `app.bin` and `cfg_tool.bin`
  pass their CRC16s.

## What is in it

Compared with the stock firmware package `SMK-37 Pro_016.fwsc` (its `flash.bin`):

| Range | Contents | Unique to this unit? |
| --- | --- | --- |
| 0x00000-0x03FFF | flash header, stock bootloader (`uboot.boot`), boot config (`isd_config`) | no: identical to the package |
| 0x04000-0x9CFFF | app area: stock 016 `app.bin` and `cfg_tool.bin` | no: identical to the package |
| 0x9D000-0xBFFFF | VM: settings store (20,619 bytes used) | **yes** |
| 0xC0000-0xC0FFF | BTIF: Bluetooth data (3,594 bytes used) | **yes** |
| 0xC1000-0xC1FFF | USRTRIM: factory key, pad and wheel calibration (556 bytes used) | **yes: cannot be recreated** |
| 0xC2000-0xEAFFF | USRFLASH: user data, probably presets (85,518 bytes used) | **yes** |
| 0xEB000-0xF3FFF | not listed in the region table | empty |
| 0xF4000-0xFDFFF | USR: stock resources (37,385 bytes; installed from the package's resource file, not its `flash.bin`) | no |
| 0xFE000-0xFEFFF | not listed (SLOOP keeps settings here on the FM-1) | empty |
| 0xFF000-0xFFFFF | key_mac | empty on this unit (all 0xFF) |

The stock firmware itself can always be put back from M-Vave's package. Only
this dump has the calibration, Bluetooth data, settings and presets.

## How it was taken

The stock firmware has no way into the chip's mask-ROM download mode (UBOOT),
so a JieLi USB_KEY dongle did it: a Raspberry Pi Pico running
`usbkey-pico/main.py` (MicroPython 1.29.0) sends the ROM's boot key 0x16EF on
the USB data lines at power-on.

1. Pico GP2 to D+, GP3 to D-, GND to GND on a USB-A breakout, with 2.2 kOhm
   pull-ups from 3V3(OUT) to D+ and to D-; breakout VBUS not connected. The
   keyboard's A-to-C cable plugged into the breakout.
2. Keyboard off (it runs from its battery); Pico sending; keyboard switched
   on. The ROM acknowledged (both lines low), the Pico let go of the lines.
   The Pico's LED shows where it is: slow blink while the unit is off, fast
   blink once it is on, steady when the ROM has acknowledged (move the cable
   now). The script only takes a short low pulse after a key as the
   acknowledge: a switched-off unit holds the lines low much longer (the
   FM-1 also lets them float up now and then), which an earlier version
   mistook for one.
3. The cable's A plug moved from the breakout to the PC. The keyboard
   enumerated as `WL80UBOOT1.00` (USB) / `WL82 UBOOT1.00` (SCSI disk).
4. On Linux, with [jl-uboot-tool](https://github.com/kagaimiq/jl-uboot-tool)
   (commit adb3f18):

   ```sh
   sudo venv/bin/python jluboottool.py --device /dev/sg0 --chip wl82 "read 0 0x100000 smk37-dump-1.bin"
   sudo venv/bin/python jluboottool.py --device /dev/sg0 --chip wl82 "read 0 0x100000 smk37-dump-2.bin"
   ```

   The tool runs its loader in RAM; reading writes nothing to the flash.
5. Keyboard switched off and on: back to the stock firmware.

This also showed that the USB_KEY dongle works on the SMK-37 Pro, so the
download mode can be reached whatever is in the flash.

## Restoring

Only if something was damaged, in download mode (steps 1-3 above), with the
same tool. Work in whole 4 KiB sectors: erase, write, read back, compare. For
example, the calibration only:

```sh
dd if=smk37-dump.bin of=usrtrim.bin bs=4096 skip=$((0xC1000 / 4096)) count=1
sudo venv/bin/python jluboottool.py --device /dev/sgN --chip wl82 "erase 0xC1000 0x1000"
sudo venv/bin/python jluboottool.py --device /dev/sgN --chip wl82 "write 0xC1000 usrtrim.bin"
sudo venv/bin/python jluboottool.py --device /dev/sgN --chip wl82 "read 0xC1000 0x1000 check.bin"
cmp usrtrim.bin check.bin
```

- The stock app area (0x04000-0x9CFFF) comes back more simply by installing the
  stock package with M-Vave's updater.
- Write 0x00000-0x03FFF (bootloader) only to undo a bootloader change, and only
  from this dump.
- Writing the whole dump back restores the unit exactly as it was on
  2026-10-13.
