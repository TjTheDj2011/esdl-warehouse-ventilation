# Bench Rebuild — Layout and Staged Bring-Up

Written for the rebuild after the 2026-09-24 session. The first build was
assembled all at once and then debugged as a whole, which cost most of a day:
when eight subsystems come up together, a single bad part looks like a fault in
every one of them.

This sheet fixes that two ways. The layout keeps the parts that fail
reachable, and the bring-up brings them up **one at a time, each verified before
the next goes in.**

---

## 1. Physical layout

Two breadboards butted end to end, ESP32 straddling the seam (that is why there
are two — the WROOM-32 is too wide to leave jumper room on a single board).

```
        +---------------- board A ----------------+---------------- board B ----------------+
 5V  ===|=========================================|=========================================|  motor supply +5V
 GND ===|=========================================|=========================================|  common ground
        |                                         |                                         |
        |   [ DS18B20 in ]   [ DS18B20 out ]      |   [ DRV8833 ]        [ buzzer ]         |
        |                                         |      ^ keep this edge clear             |
        |   [ ESP32 -- straddles the seam ---------------]                                  |
        |                                         |                                         |
        |   [ OLED IN ]  [ OLED OUT ]             |   [ OLED STATE ]                        |
        +-----------------------------------------+-----------------------------------------+
```

Rules that earn their keep:

- **Driver on an outside edge, output pins facing out.** Those are the pins we
  probe and the pins that fail. Do not bury them between other parts.
- **One rail pair only.** Pick one 5 V rail and one ground rail and jumper every
  other rail to them. Multiple ungrounded rails is how "common ground" quietly
  stops being true.
- **Ground first, always.** Ground jumpers go in before anything else and come
  out last. A driver without a ground reference sees garbage on its logic inputs
  and reports no error at all.
- **Colour discipline.** Red = 5 V, black = ground, any other colour = signal.
  No exceptions, because the one exception is the wire you will misread at 1 a.m.
- **Leave GPIO 33 empty.** It is the node classifier's control pin.
- **Label the fan leads** with tape: `INTAKE` and `EXHAUST`. They are identical
  and swapping them inverts the whole control law with no error message.

## 2. Pin map

Authoritative table is [01_pinout.md](01_pinout.md). Summary for the bench:

| Signal | GPIO | | Signal | GPIO |
|---|---|---|---|---|
| DS18B20 inside | 4 | | DRV8833 AIN1 (intake) | 25 |
| DS18B20 outside | 16 | | DRV8833 AIN2 (intake) | 26 |
| I2C0 SDA (OLED IN/OUT) | 21 | | DRV8833 BIN1 (exhaust) | 27 |
| I2C0 SCL | 22 | | DRV8833 BIN2 (exhaust) | 14 |
| I2C1 SDA (OLED STATE) | 17 | | DRV8833 nSLEEP | 13 |
| I2C1 SCL | 18 | | Buzzer module | 23 |
| Bench probe | 32 | | **Leave unwired** | **33** |

Power: DRV8833 **VM to the 5 V motor supply**, never to the ESP32's 3.3 V rail
or through USB. DRV8833 GND to the common ground rail.

## 3. Staged bring-up

Do these in order. **Do not wire stage N+1 until stage N passes.** Each stage
has a command that proves it, so a failure is attributable to the part you just
touched instead of to the whole system.

| # | Wire this | Run this | Passes when |
|---|---|---|---|
| 0 | ESP32 + USB only | `node` | Control GPIO 33 reads `floating, as it must be`. Proves the instrument before it judges anything. |
| 1 | Both DS18B20s | `status` | Two plausible temperatures, `fail=0`. Pinch one sensor and watch it rise. |
| 2 | OLED IN + OUT (bus 0) | `scan` | `0x3C` and `0x3D` on bus 0. Both panels show numbers. |
| 3 | OLED STATE (bus 1) | `scan` | `0x3C` on bus 1. Third panel shows a state word. |
| 4 | Buzzer | `buzz` | Audible, and **silent at power-up** (it is active-low). |
| 5 | DRV8833: GND, VM, nSLEEP **only** — no fans | `diag` | `nSLEEP: HIGH (enabled)`. Power LED lit. |
| 6 | Probe GPIO 32 to **OUT1**, no fans | `node` then `probe a` | `node` = **FLOATING**. `probe a` = **coast=HIGH brake=LOW**. This is the test the old driver failed. |
| 7 | Same probe on **OUT3** | `node` then `probe b` | Same result. Anything reading **TIED TO GROUND** means stop — that board is bad. |
| 8 | Remove probe. Intake fan on OUT1/OUT2 | `intake on` | It spins. Red lead to OUT1, black to OUT2. |
| 9 | Exhaust fan on OUT3/OUT4 | `exhaust on` | It spins. |
| 10 | Everything | `sim` through all five states | Fans and buzzer match [03_control_matrix.md](../docs/03_control_matrix.md). |

**Stage 6 is the gate.** It is the first test that exercises the driver chip
itself rather than the wiring to it, and it takes ten seconds. Run it before you
plug a single fan in — a bad driver found at stage 6 costs nothing, and the same
bad driver found at stage 8 looks like a fan problem, a power problem and a
wiring problem simultaneously. That is the day we just lost.

## 4. What the probe can and cannot tell you

Worth knowing so the results are not over-read:

- `wire <gpio>` runs ESP32 → wire → back to ESP32. It **never passes through the
  driver chip.** WIRE GOOD proves the jumper and the breadboard row conduct. It
  would pass with the driver physically removed, so it cannot clear a cold solder
  joint on the driver's header.
- `probe a` / `probe b` **do** go through the chip — brake pulls an output to
  ground using the chip's own transistor. This is the only test that needs the
  driver to work.
- `node` classifies one node as floating, grounded or tied high, and validates
  itself against unwired GPIO 33 first.
- `diag`'s nFAULT line can confirm a fault but never health: open-drain reads
  "no fault" on a dead or absent chip.

## 5. Recorded failure — 2026-09-24

First DRV8833 was replaced, not repaired. Measured with nothing attached:

| Node | Reading | Meaning |
|---|---|---|
| OUT1 | `coast=HIGH brake=HIGH` | chip not driving it |
| OUT2 | `coast=HIGH brake=HIGH` | chip not driving it |
| OUT3 | `pullup=LOW pulldown=LOW`, 3/3 | tied to ground |

Everything upstream measured good: common ground confirmed at the driver's GND
pin, all four input wires and nSLEEP reached their rows, VM present, nFAULT not
asserted, both fans verified spinning on the bare 5 V rail, both DS18B20s and
both OLEDs working. Three dead outputs with nothing connected condemned the
board.

Two of the day's "faults" were the instrument's own and are fixed: the wire
probe left its drive pin low and stranded the driver asleep, and `diag` scaled
readings by a voltage divider that was never fitted. Both are why stage 0 exists
and why `node` validates its control before reporting a verdict.
