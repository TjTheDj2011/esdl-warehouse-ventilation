# Hardware Checklist

Tick these off against the actual parts in front of you. Status as of
2026-09-21, end of week 4 of 7 — about 2.5 weeks remain.

---

## 1. Have it — confirm each is physically present

| ✓ | Part | Qty | Check |
|---|---|---|---|
| ☐ | ESP32-WROOM-32 dev board | 1 + spares | USB-C, boots when plugged in |
| ☐ | Breadboards, butted together | 2 | ESP32 seats with both pin rows accessible |
| ☐ | **DS18B20** temperature sensor | 2 | Black TO-92 on a small board, marked `DS18B20` |
| ☐ | **Elegoo SSD1306 OLED**, 0.96", 128x64, I2C | 3 | 4 pins: VCC GND SCL SDA · 3.3-5V · ~20 mA · **address select on the back, confirmed** |
| ☐ | **Active buzzer** | 1 | Marked active. Makes a continuous tone on DC, not a click |
| ☐ | Jumper wires | ~40 | Mix of M-M and M-F |
| ☐ | Assorted resistors | — | Need 2x **4.7 kΩ** if the DS18B20s are bare (see §4) |

## 2. In the cart — confirm before checkout

| ✓ | Part | Qty | Check the listing says |
|---|---|---|---|
| ☐ | 80 mm brushless fan, **5 V** | **2** | 5 V not 12 V · 2-pack not single · 80x80 frame |
| ☐ | 5 V **2 A** wall supply | 1 | 5 V, 2 A, and it ships with the screw-terminal adapter |

## 3. Still to buy — NOTHING

| ✓ | Part | Qty | ~$ | Note |
|---|---|---|---|---|
| ☑ | ~~**DRV8833** dual motor driver~~ | 1 | | **In hand.** |

## 4. Verify before wiring — ALL FOUR ANSWERED

**☑ DS18B20 pull-up — PRESENT. CONFIRMED 2026-09-21.**
The 4.7 kΩ is onboard, next to the black sensor. Nothing to add.

**☑ Buzzer — 3 pins, active. CONFIRMED.**
Module with an onboard transistor. Wires straight to GPIO 23, no NPN needed,
and active means the firmware's plain high/low switching is correct.

**☑ OLED address select — CONFIRMED PRESENT.**
Move the address select on **one** module to 0x3D; that becomes the OUT panel.
Leave the other two at 0x3C. Do one, verify it with the firmware self-test
(it prints each panel's address), then stop. You have a spare if it goes wrong.

**☑ Supply polarity — MARKED. CONFIRMED 2026-09-21.**
Terminals are labelled. Wire + to the fan rail, − to the common ground rail.

## 5. Mechanical — still to source

| ✓ | Item | ~$ | Note |
|---|---|---|---|
| ☐ | Clear plastic tote | 8–15 | **Polypropylene, not acrylic** — acrylic cracks when drilled |
| ☐ | 76 mm hole saw or step bit | 8–15 | For the two fan openings |
| ☐ | 4.5 mm drill bit | — | For the fan screw holes |
| ☐ | M4 screws, nuts, washers | 5 | 8 of each — four per fan |
| ☐ | Foam weatherstrip tape | 3 | Gasket between fan and tote; kills vibration |
| ☐ | Hair dryer | on hand? | Demo heat source. **Not a heat gun** — it melts polypropylene |
| ☐ | Masking tape | ~0 | Labelling the four power rails |

## 6. Tools

| ✓ | Item | Needed for |
|---|---|---|
| ☐ | Drill | Fan holes |
| ☐ | Multimeter | Supply polarity, continuity. Borrow from the lab if needed |
| ☐ | Soldering iron | Only to tin the fan leads after cutting connectors. Optional |

---

## What you do NOT need any more

Struck through because the design moved on — do not buy these:

- ~~16x2 LCD + PCF8574 backpack~~ — replaced by three OLED panels
- ~~BSS138 level shifter~~ — every peripheral is 3.3 V native now
- ~~DHT22 sensors~~ — the DS18B20s are better
- ~~0.1 uF suppression capacitors~~ — brushless fans have no brush noise
- ~~4xAA battery pack~~ — replaced by the 5 V wall supply
- ~~130-size brushed motors~~ — replaced by brushless fans
- ~~Backdraft flapper, drilled makeup holes~~ — the idle intake fan is the vent
- ~~Barrel-jack to screw-terminal adapter~~ — the supply ships with one

---

## Bottom line

**ELECTRONICS COMPLETE.** Every part is in hand and every open question in §4 is
answered. Nothing further to buy on the electrical side.

Remaining work is mechanical (§5) and bring-up. Wiring can start now - the
electronics do not depend on the enclosure.
