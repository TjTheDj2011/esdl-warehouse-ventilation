# Bring-Up Guide

For the session where components meet the breadboard. Wiring reference is
`hardware/01_pinout.md`; parts list is `hardware/05_hardware_checklist.md`.

**The one rule: add one peripheral at a time, and confirm it before adding the
next.** If everything goes on at once and the board misbehaves, you have five
suspects and no way to separate them. The firmware is built for this — every
peripheral can be exercised on its own from the serial console.

Open the serial monitor at **115200 baud** and type `help` at any point.

---

## Before power: what can actually damage something

The old version of this guide warned about 5 V level shifting. **That risk is
gone** — every peripheral is now 3.3 V native. What remains:

1. **Fan power is separate.** The 5 V 2 A adapter feeds the DRV8833's VM only.
   Never the ESP32's 3.3 V pin, never USB through the board. Both fans start
   together and their inrush would exceed a USB port.
2. **Common ground is mandatory.** The adapter's negative ties to the ESP32 GND
   rail. Without it the driver has no reference and the usual symptom is motors
   that do nothing, or twitch randomly.
3. **Check DRV8833 orientation and supply polarity** before applying power.
   Reversed VM and GND kills the chip instantly.
4. **Never bridge two different + rails.** You have four rail pairs across two
   breadboards. 3.3 V and 5 V tied together destroys the ESP32. Label them.

## Power rails

| Rail pair | + carries | Feeds |
|---|---|---|
| A | **3.3 V** from the ESP32 `3V3` pin | OLEDs, DS18B20s, buzzer |
| B | **5 V** from the wall adapter | DRV8833 `VM` only |
| C/D | spare | extra ground |

**All blue (−) rails jumper together.** Every + rail stays separate.
Label them with masking tape before you wire anything.

---

## Step 1 — Board alone

Plug in the USB-C cable. Nothing else connected.

Expected in the serial monitor:

```
ESDL Project 1 -- ventilation controller
=== power-on self test ===
I2C bus 0      : 0 device(s)
I2C bus 1      : 0 device(s)
OLED IN        : NOT FOUND
OLED OUT       : NOT FOUND
OLED STATE     : NOT FOUND
DS18B20 inside : 0 probe(s) on GPIO 4
DS18B20 outside: 0 probe(s) on GPIO 16
```

After about 7.5 seconds it enters **FAULT**. **That is a pass.** No sensors
means no trustworthy data, and the controller is built to fail loud rather than
sit quietly in STANDBY.

Nothing on serial at all? In order: wrong baud, a **charge-only USB-C cable**,
or on Linux you are not in the `dialout` group:

```bash
sudo usermod -a -G dialout $USER     # then log out and back in
```

## Step 2 — OLED panels

**First, move one module to 0x3D.** On the back, find `IIC ADDRESS SELECT` with
`0x78` and `0x7A` either side. Remove the 0 ohm resistor bridging the `0x78`
side and bridge the `0x7A` side instead. That module becomes **OUT**.

**Never bridge both** — the outer pads are VCC and GND, so bridging both shorts
the 3.3 V rail.

Then wire all three:

| Panel | Bus | SDA | SCL | Address |
|---|---|---|---|---|
| IN | 0 | GPIO 21 | GPIO 22 | 0x3C |
| OUT | 0 | GPIO 21 | GPIO 22 | **0x3D** |
| STATE | 1 | GPIO 17 | GPIO 18 | 0x3C |

All three take VCC from the 3.3 V rail and GND from the ground rail.

Reset and check the self test names all three. Or type `scan` to list every
device on both buses, then `oled` to re-probe without rebooting.

- **OUT reports at 0x3C** — the address resistor did not move
- **OUT reports NOT FOUND** — the new bridge is not making contact
- **A panel is missing entirely** — SDA/SCL swapped, or no 3.3 V

A missing panel is not fatal. The controller keeps running and the serial trace
is the fallback display.

## Step 3 — Temperature sensors

Add the chamber DS18B20 on **GPIO 4** first, then the ambient one on **GPIO 16**.
Each module has its 4.7k pull-up onboard, so it is three wires each: VCC to
3.3 V, GND to ground, data to the GPIO.

Reset and confirm the self test reports `1 probe(s)` on each pin. Then:

- `status` shows live readings and `ok` / `fail` counts per sensor
- Watch the `fail` counter for a minute. It should stay at zero. A climbing
  count means a marginal connection — fix it now, not during the demo.
- `0 probe(s)` on a pin means no pull-up reaching that data line, or the wrong
  pin

Both reading and the chamber below 77 F should settle the state to `STANDBY`.

## Step 4 — Motor driver and fans

**Fans on the wall adapter. Common ground.** Wire the DRV8833 first, power it,
and confirm before connecting fans:

| DRV8833 | To |
|---|---|
| VM | adapter **+** (5 V) |
| GND | adapter **−** *and* the ESP32 ground rail |
| SLP / nSLEEP | GPIO 13 |
| AIN1 / AIN2 | GPIO 25 / 26 → intake fan |
| BIN1 / BIN2 | GPIO 27 / 14 → exhaust fan |

Fans are 2-wire and polarised: red to the first output of the pair, black to
the second. Test each channel on its own:

```
intake on        intake fan spins
intake off
exhaust on       exhaust fan spins
exhaust off
auto             hand the pins back to the control loop
```

`intake rev` exists to prove both half-bridges are wired, but a brushless fan
cannot reverse — it will simply stop. That is expected, not a fault.

Any motor command enters **MANUAL OVERRIDE**: the control loop keeps running and
tracing but stops driving the pins. Every trace line says `[MANUAL OVERRIDE]`
and the panels show an `M` marker. It reverts to AUTO automatically after five
minutes so nothing runs unattended.

**Confirm airflow direction physically.** Every fan has a moulded arrow on the
frame. Confirm with power anyway — intake must blow **in**, exhaust must blow
**out**. Mark each one. A fan mounted backwards quietly ruins the demo.

Nothing moves? In order: `nSLEEP` not high, no common ground, DRV8833
orientation, supply polarity.

## Step 5 — Buzzer

Three-pin active module: VCC to 3.3 V, GND to ground, I-O to **GPIO 23**.

```
buzz on          steady tone (thermal overload alarm)
buzz pat         4 Hz intermittent (sensor fault)
buzz off
auto
```

## Step 6 — Closed loop, no heat needed

Drive the state machine directly and prove every transition before any heat is
involved:

```
sim 72 65        STANDBY       -- below setpoint
sim 85 65        CROSS_VENT    -- hot, outside cooler, both fans run
sim 85 84        EXHAUST_ONLY  -- hot, outside close, exhaust only
sim 85 95        SEALED        -- outside hotter, both fans stop, alarm
sim 78.5 65      still CROSS_VENT (hysteresis releases at 77, not 79)
sim 74 65        STANDBY       -- released
sim off          back to the real sensors
```

Allow about **10 seconds between commands** — the minimum state dwell
deliberately blocks faster transitions. That is the anti-chatter guard working.

While simulation is active every panel shows an `S` marker and every trace line
says `[SIMULATED INPUT]`. **Simulated readings are not evidence.** Use this to
rehearse and verify wiring, then take real measurements for anything that goes
in the report.

**To demonstrate FAULT:** unplug one DS18B20's data wire. It reports −127 C,
which fails the range check, and after three consecutive bad reads the
controller enters FAULT — exhaust still running, buzzer pattern, `SENSOR FAULT`
scrolling on the state panel. It never falls silently into STANDBY.

## Step 7 — Real heat

- Keep the ambient sensor well clear of the exhaust. If it reads our own hot
  exhaust, the controller sees outside as hotter and latches `SEALED` forever —
  a positive feedback loop that looks exactly like a firmware bug.
- Shield the chamber sensor from direct heat-gun IR so it reads air temperature
  rather than radiant heat.
- **Hair dryer, not a heat gun.** A heat gun melts a polypropylene tote.
- Capture the serial trace to a file. Those transitions are the measurements the
  report is built on.

---

## Symptom → cause

| Symptom | Look here first |
|---|---|
| Nothing on serial | Baud 115200 · charge-only USB cable · `dialout` group |
| `scan` finds nothing | SDA/SCL swapped · no 3.3 V · common ground |
| OUT panel at 0x3C | Address resistor did not move |
| A panel blank but detected | Its `display()` is running — check the ribbon seating |
| Sensors show `--.-` | Wrong pin, or `0 probe(s)` in the self test |
| `fail` count climbing | Marginal connection on that data line |
| Board resets when fans start | Fans drawing from USB instead of the adapter |
| Motors do nothing | nSLEEP low · no common ground · DRV8833 orientation |
| Stuck in SEALED | Ambient sensor sitting in the exhaust plume |
| Fans hunt on and off | Should not happen — hysteresis and dwell prevent it. Report it |
| State never changes | Check `status` for `fail` counts; a FAULT masks normal states |

## What "working" means here

Compiling is not working. Simulated input is not working. A step is done when
you have seen the real behaviour and, where the report will cite it, captured
the serial trace that shows it.
