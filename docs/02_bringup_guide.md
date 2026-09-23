# Bring-Up Guide

For the session where components meet the breadboard. Wiring reference is
`hardware/01_pinout.md`.

**The one rule: add one peripheral at a time, and confirm it before adding the
next.** If everything goes on at once and the board misbehaves, you have five
suspects and no way to separate them. The firmware is built for this — every
peripheral can be exercised on its own from the serial console.

Open the serial monitor at **115200 baud** and type `help` at any point.

---

## Before power: three things that damage parts

1. **The LCD must go through the BSS138 level shifter.** The PCF8574 backpack
   runs at 5V, so its pull-ups sit on SDA/SCL at 5V. The ESP32 is not 5V
   tolerant — 3.6V is the absolute maximum on a GPIO. Low side of the shifter to
   3.3V, high side to 5V.
2. **Motor power never comes from the ESP32.** Not the 3.3V pin, not 5V through
   the board. Brushed inrush browns out the MCU. Separate supply into the
   DRV8833 VM pin.
3. **Common ground is mandatory.** Battery negative ties to ESP32 GND. Without
   it the driver has no reference and sees no valid logic level — the usual
   symptom is motors that do nothing, or twitch randomly.

Double-check DRV8833 orientation before applying power. Reversed VM and GND
kills the chip immediately.

---

## Step 1 — Board alone

Flash the firmware with nothing else connected.

Expected: the power-on self test prints, reports `I2C devices : 0`, `LCD : NOT
FOUND`, and both DHT22s as `no reading yet`. **That is a pass.** The controller
enters FAULT after about 7.5 seconds with nothing attached, which is correct —
no sensors means no trustworthy data.

If you see nothing at all, it is the baud rate or the USB cable. Plenty of cheap
USB-C cables are charge-only.

## Step 2 — LCD

Wire it through the level shifter, then reset the board.

- Self test should report `LCD : attached at 0x27` (or `0x3F`).
- The firmware probes **both** addresses automatically, so you do not need to
  know which batch you have.
- Type `scan` to list everything on the bus.

If `scan` finds nothing: level shifter powered on *both* sides, SDA and SCL not
swapped, common ground present. If the backlight is on but the screen is blank
or shows white blocks, turn the contrast trimmer on the back of the backpack.

The display is optional to the controller — if it never attaches, the system
keeps running and the serial trace is the display. Nothing else is blocked.

## Step 3 — Sensors

Add the chamber DHT22 first, on GPIO 4. Then the ambient one on GPIO 16.

- `status` shows live readings plus `ok` / `fail` counts per sensor.
- A failed first read after power-up is normal.
- Persistent failures: check the 10k pull-up (breakout modules have it), and
  confirm 3.3V power. At 3.3V the data line is already at logic level, so no
  shifter is needed here.
- Watch the `fail` counter over a minute. It should stay at or near zero. A
  climbing count means a marginal connection — fix it now, not during the demo.

Once both read, the state should settle to `STANDBY` at room temperature.

## Step 4 — Motors

**Motors off the board's power. Separate supply, common ground.** Solder a
0.1 uF ceramic across each motor's terminals before wiring them in — brush noise
corrupting the I2C bus is the most common failure in this exact build, and it
presents as a *display* problem, which sends people debugging the wrong thing.

Test each channel independently:

```
intake on        intake fan spins
intake rev       same fan, opposite direction (proves both half-bridges)
intake off
exhaust on
exhaust off
auto             hand the pins back to the control loop
```

Any motor command puts the rig in **MANUAL OVERRIDE** — the control loop keeps
running and tracing but stops driving the pins. The serial trace says
`[MANUAL OVERRIDE]` on every line and the LCD shows `M` in the bottom-right
corner. It reverts to AUTO automatically after 5 minutes so nothing runs
unattended.

Confirm airflow direction physically. Intake should blow *in* at bottom-left,
exhaust should pull *out* at top-right. A propeller mounted backwards is easy to
miss and quietly ruins the cross-ventilation demo.

## Step 5 — Buzzer

```
buzz on          steady tone (thermal overload alarm)
buzz pat         4 Hz intermittent (sensor fault)
buzz off
auto
```

Use a buzzer *module* with an onboard transistor. A bare element draws about
30 mA, over the 20 mA a GPIO should source.

## Step 6 — Closed loop, no heat gun

You can drive the state machine directly to prove every transition before any
heat is involved:

```
sim 72 65        STANDBY      -- below setpoint
sim 82 65        CROSS_VENT   -- hot, outside cooler, both fans
sim 82 88        EXHAUST_ONLY -- hot, outside hotter, exhaust + alarm
sim 78.5 65      still CROSS_VENT (hysteresis: releases at 77, not 79)
sim 76 65        STANDBY      -- released
sim off          back to the real sensors
```

Allow ~10 seconds between commands — the minimum state dwell deliberately
blocks faster transitions.

While simulation is active the LCD shows `S` in the top-right corner and every
trace line says `[SIMULATED INPUT]`. **Simulated readings are not evidence.**
Use this to rehearse and to verify wiring, then take real measurements with the
heat source for anything that goes in the report.

## Step 7 — Real heat

- Keep the ambient sensor well clear of the exhaust plume. If it reads our own
  hot exhaust, the system latches EXHAUST_ONLY forever — a positive feedback
  loop that looks exactly like a firmware bug.
- Shield the chamber sensor from direct heat-gun IR so it reads air temperature
  rather than radiant heat.
- Capture the serial trace to a file. Those transitions are the measurements the
  report is built on.

---

## Symptom → cause

| Symptom | Look here first |
|---|---|
| Nothing on serial | Baud 115200; charge-only USB cable |
| `scan` finds no devices | Level shifter unpowered on one side; SDA/SCL swapped; no common ground |
| LCD backlit but blank | Contrast trimmer on the backpack |
| LCD garbles when fans run | Missing 0.1 uF across the motors — brush noise on I2C |
| Board resets when a fan starts | Motors drawing from the board instead of their own supply |
| Sensors read `--.-` | Wrong pin, missing pull-up, or not on 3.3V |
| Stuck in EXHAUST_ONLY | Ambient sensor sitting in the exhaust plume |
| Motors do nothing | nSLEEP not high; no common ground; DRV8833 orientation |
| Fans hunt on and off | Should not happen — hysteresis and dwell prevent it. Report it. |
| State never changes | Check `status` for `fail` counts; a FAULT masks normal states |

## What "working" means here

Compiling is not working. Simulated input is not working. A step is done when
you have seen the real behaviour and, where the report will cite it, captured
the serial trace that shows it.
