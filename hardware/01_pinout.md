# Pin Assignment — ESP32-WROOM-32

**Board selected:** ESP32-WROOM-32 (USB-C, WiFi + BT 4.2). Several on hand.
**Backup / upgrade path:** ESP32-S3 N16R8 — see the appendix at the bottom.

Chosen over the S3 for two practical reasons: we own **spares** of this one, and
it is by a wide margin the best-documented ESP32 for the exact peripheral mix in
this build. Neither WiFi nor Bluetooth is used — this is a self-contained local
controller by design.

> Verify against your board's actual silkscreen before wiring. USB-C ESP32 boards
> ship in 30-pin and 38-pin variants and the 30-pin ones omit several GPIO.

## Pins that are unavailable on this part

| GPIO | Why it is off-limits |
|---|---|
| 6-11 | SPI flash interface. Using these will crash the chip. |
| **34, 35, 36, 37, 38, 39** | **INPUT ONLY.** Cannot drive an output at all, and have no internal pull-ups. |
| 0, 2, 5, 12, 15 | Strapping pins, sampled at reset. |
| 1, 3 | UART0 TX/RX — the serial console we need for the debug trace. |
| 2 | Also the onboard LED on most boards. |

Two traps worth calling out specifically, because both produce confusing symptoms
rather than obvious failures:

- **GPIO 34-39 are input-only.** Wire the motor driver to GPIO 34 and you get
  silence with no error — the pin simply cannot drive. This quirk is unique to the
  classic ESP32; the S3 does not have it.
- **GPIO 12 (MTDI) must be LOW at boot.** It selects the flash voltage. Held high
  by something you attached, the board may fail to boot at all.

Note this is a **different forbidden set than the ESP32-S3**. The S3 loses 33-37 to
octal PSRAM and has no input-only pins; this part loses 34-39 to input-only and
6-11 to flash. Do not carry an S3 pinout across.

## Assignment

Safe working pins on this board: **4, 13, 14, 16, 17, 18, 19, 21, 22, 23, 25, 26,
27, 32, 33.** Fifteen available, ten used.

| Signal | GPIO | Notes |
|---|---|---|
| DS18B20 — inside / chamber | 4 | 1-wire. **4.7k pull-up to 3.3V**; breakout modules include it. |
| DS18B20 — outside / ambient | 16 | Same. Keep well clear of the exhaust plume. |
| I2C bus 0 SDA | 21 | OLED panels IN (0x3C) and OUT (0x3D) |
| I2C bus 0 SCL | 22 | |
| I2C bus 1 SDA | 17 | OLED panel STATE (0x3C) |
| I2C bus 1 SCL | 18 | |
| DRV8833 AIN1 — intake fan | 25 | |
| DRV8833 AIN2 — intake fan | 26 | |
| DRV8833 BIN1 — exhaust fan | 27 | |
| DRV8833 BIN2 — exhaust fan | 14 | |
| DRV8833 nSLEEP | 13 | Drive HIGH to enable the bridge. |
| Buzzer | 23 | Buzzer *module* with onboard transistor. |

| DRV8833 nFAULT (optional) | 19 | Open-drain, `INPUT_PULLUP`. See the caveat below. |
| Bench probe / sense | 32 | Continuity probe and node classifier. Not needed for the demo. |

**GPIO 33 must be left unwired.** The `node` classifier reads it as a control to
prove the pull resistors and the read path work before it reports a verdict on
any other node. Wire something to 33 and the classifier can no longer tell a
genuine short from a firmware fault.

**nFAULT proves less than it looks like it does.** It is open-drain, held up by
the internal pull-up, so an *unpowered or absent* DRV8833 reads exactly the same
"no fault" as a healthy one. It can confirm a fault; it can never confirm health.

**Never leave a bare jumper from GPIO 32 to an OUT pin while the fans can run.**
A driven output sits at VM (5 V) and the ESP32 is not 5 V tolerant. `probe` is
safe because it only ever uses coast and brake, which never drive an output high;
`diag` skips its FORWARD step for the same reason unless `SENSE_HAS_DIVIDER` is
set. For permanent monitoring, fit a 1:1 divider (two equal resistors, 10k/10k)
from the output to ground and tap the middle.

**Why two I2C buses.** Three identical SSD1306 panels are hardwired to 0x3C,
and the address-select pad on the back offers only one alternative, 0x3D. Two
addresses cannot serve three panels, so bus 0 carries two and bus 1 carries
the third. The ESP32 has two hardware I2C peripherals, so this costs two GPIO
and no extra parts.

## Power and signal levels

- Both DS18B20s run from the **3.3V** rail and connect **directly** to GPIO.
  Each data line needs a 4.7k pull-up to 3.3V; breakout modules include it.
  They could share one pin (each has a unique 64-bit ROM id) but separate
  pins keep "the one on GPIO 4 is inside" true without enumerating addresses.
- The ESP32 is **not** 5V tolerant. Neither is the S3. Nothing changed here.

## Wiring rules that are not optional

1. **No level shifter anywhere.** Every peripheral is 3.3 V native: the SSD1306
   OLED panels, both DHT22s and the DRV8833. This falls out of choosing OLEDs
   over a 5 V HD44780 LCD, and it removes the most dangerous wiring mistake
   the earlier design allowed.
2. **Separate motor supply.** Motor power never comes from the 3.3V rail or from
   USB through the board. Brushed inrush will brown out the MCU mid-demo. Battery
   negative ties to ESP32 GND — **common ground is required**, or the driver never
   sees a valid logic level.
3. **Brushless fans, so no suppression capacitors.** Brush noise corrupting the
   I2C bus was the most common failure in the earlier brushed-motor design.
   That failure mode is designed out rather than mitigated.
4. **An idle fan is the makeup-air vent, by design.** In EXHAUST_ONLY the
   exhaust runs while the intake sits still and air enters through it, low and
   on the far wall. Safe by construction: if outside were meaningfully hotter
   we would be in SEALED with both fans stopped.

## Appendix — ESP32-S3 N16R8 (backup board)

If the WROOM-32 boards are exhausted, the S3 works with a **different** pin map.
`R8` means 8 MB octal PSRAM, whose die is bonded to GPIO 33-37 inside the module,
so those five pins are unusable even though this project never initialises PSRAM.

Forbidden on the S3: 0/3/45/46 (strapping), 19/20 (USB), 26-32 (flash), **33-37
(octal PSRAM)**, 43/44 (UART0), 48 and sometimes 38 (onboard RGB LED).
Safe range: **4-18 and 21.** The S3 has **no** input-only pins.

Suggested S3 map: DHT in 4, DHT out 5, SDA 8, SCL 9, AIN1 10, AIN2 11, BIN1 12,
BIN2 13, nSLEEP 14, buzzer 21.

The control firmware is hardware-agnostic and needs no changes to move between the
two boards — only this pin table does.
