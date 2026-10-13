# JieLi USB_KEY sender for a Raspberry Pi Pico (MicroPython).
#
# Clocks the mask ROM's boot key 0x16EF onto the target's USB lines
# (D+ = clock, the chip latches D- on its rising edge; MSB first) until the
# chip acknowledges by pulling both lines low for 1-2 ms. Then it lets go of
# the lines: move the target's USB cable to the PC, which should find a
# "WL82 UBOOT1.00" disk.
#
# Wiring (USB-A breakout, the keyboard's A-to-C cable plugged into it):
#   GP2 (pin 4)     -> D+  (green)
#   GP3 (pin 5)     -> D-  (white)
#   GND (pin 3)     -> GND
#   3V3(OUT) (pin 36) -> 2.2 kOhm -> D+
#   3V3(OUT) (pin 36) -> 2.2 kOhm -> D-
#   breakout VBUS: not connected
#
# The lines are driven open-drain (low, or released to the pull-ups), so the
# chip's acknowledge never fights the Pico. While the keyboard is off, its
# unpowered chip clamps the lines low too, so an acknowledge only counts once
# the released lines have read high (keyboard on). LED: slow blink = waiting
# for the keyboard, fast blink = keyboard on, steady = acknowledged (swap the
# cable now), off = gave up after TIMEOUT_S.
from machine import Pin
import time

KEY = 0x16EF
HALF_US = 10        # 50 kHz clock; the ROM receives in software, timing is loose
GAP_US = 150        # lines released between keys; the acknowledge is sampled here
TIMEOUT_S = 60

clk = Pin(2, Pin.OPEN_DRAIN, value=1)      # D+
dat = Pin(3, Pin.OPEN_DRAIN, value=1)      # D-
led = Pin("LED", Pin.OUT, value=0)


def send_key():
    for i in range(15, -1, -1):
        clk.value(0)
        dat.value((KEY >> i) & 1)
        time.sleep_us(HALF_US)
        clk.value(1)                        # rising edge: the chip latches D-
        time.sleep_us(HALF_US)
    dat.value(1)                            # both released: pulled high


def lines_low():
    # Both lines held low against the pull-ups, twice in a row.
    for _ in range(2):
        time.sleep_us(GAP_US // 2)
        if clk.value() or dat.value():
            return False
    return True


def main():
    print("sending the key: switch the keyboard on")
    start = time.ticks_ms()
    n = 0
    on = False                              # released lines seen high
    while time.ticks_diff(time.ticks_ms(), start) < TIMEOUT_S * 1000:
        send_key()
        if not lines_low():
            if not on:
                print("keyboard is on")
            on = True
        elif on:
            clk.init(Pin.IN)                # let go of the lines for good
            dat.init(Pin.IN)
            led.value(1)
            print("ACK after %d keys: move the cable to the PC now" % n)
            return
        n += 1
        if n % (100 if on else 500) == 0:
            led.toggle()
    clk.init(Pin.IN)
    dat.init(Pin.IN)
    led.value(0)
    print("no acknowledge in %d s; reset the Pico to try again" % TIMEOUT_S)


main()
