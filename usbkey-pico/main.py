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
# chip's acknowledge never fights the Pico. A switched-off unit holds the
# lines low through its unpowered chip, but not reliably: the pull-ups feed it
# a little current and the lines can float up now and then (the FM-1 does).
# So an acknowledge must look like one: the released lines high before a key,
# then both low right after it for ACK_MIN_US to ACK_MAX_US, then high again.
# Lines held low longer are a switched-off unit, not an acknowledge.
#
# LED: slow blink = waiting for the unit, fast blink = unit on, sending,
# steady = acknowledged (swap the cable now), off = gave up after TIMEOUT_S.
from machine import Pin
import time

KEY = 0x16EF
HALF_US = 10        # 50 kHz clock; the ROM receives in software, timing is loose
GAP_US = 150        # lines released between keys; the acknowledge starts here
ON_MS = 20          # released lines high this long in a row: the unit is on (LED only)
ACK_MIN_US = 300    # an acknowledge holds both lines low at least this long
ACK_MAX_US = 5000   # ... and releases them within this time
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


def both_low():
    return not clk.value() and not dat.value()


def low_time_us():
    # How long both lines stay low, up to ACK_MAX_US.
    t0 = time.ticks_us()
    while both_low():
        if time.ticks_diff(time.ticks_us(), t0) >= ACK_MAX_US:
            break
    return time.ticks_diff(time.ticks_us(), t0)


def main():
    print("sending the key: switch the unit on")
    start = time.ticks_ms()
    high_since = None                       # released lines high since (ms)
    on = False
    n = 0
    while time.ticks_diff(time.ticks_ms(), start) < TIMEOUT_S * 1000:
        send_key()
        time.sleep_us(GAP_US // 2)
        if both_low():
            low = low_time_us()
            if high_since is not None and ACK_MIN_US <= low < ACK_MAX_US:
                clk.init(Pin.IN)            # let go of the lines for good
                dat.init(Pin.IN)
                led.value(1)
                print("ACK after %d keys (lines low %d us): move the cable to the PC now" % (n, low))
                return
            high_since = None
            if on and low >= ACK_MAX_US:
                on = False                  # held low: the unit is off (again)
                print("unit off: switch it on")
        else:
            now = time.ticks_ms()
            if high_since is None:
                high_since = now
            elif not on and time.ticks_diff(now, high_since) >= ON_MS:
                on = True
                print("unit is on")
            time.sleep_us(GAP_US // 2)
        n += 1
        if n % (100 if on else 500) == 0:
            led.toggle()
    clk.init(Pin.IN)
    dat.init(Pin.IN)
    led.value(0)
    print("no acknowledge in %d s; reset the Pico to try again" % TIMEOUT_S)


main()
