---
description: ESDL Project 1 workflow — hardware/firmware discipline, every task
---

# ESDL Project 1 Workflow

Scoped to this repository: ESP32-S3 warehouse ventilation controller.
This file exists to override any global `/workflow` command. Nothing from any
other project applies here.

## 0. Context
- Read `CLAUDE.md` — the state machine and the standing engineering constraints.
- Check the project memory directory for prior decisions.
- The constraints in `CLAUDE.md` are **decided**. Do not silently regress them.
  If one needs to change, say so explicitly and get TJ's agreement first.

## 1. Design before code
- State which files change and which GPIO pins, peripherals, or timing budgets
  are affected.
- Check the pin plan against the board's real constraints: strapping pins
  (0, 3, 45, 46), USB (19/20), flash/PSRAM, and GPIO 33-37 on octal-PSRAM parts.
- Identify what could break electrically, not just logically — brownout,
  I2C corruption from brush noise, 5V on a 3.3V pin.
- Write the test plan before the code.

## 2. Code
- Non-blocking only. `millis()` scheduler, zero `delay()` in `loop()`.
- Control math in Celsius; convert only at the display boundary.
- Every sensor read has an explicit failure path. NaN is a real, expected value
  and must route to FAULT — never fall through to a default state.
- Match the existing style. Minimal, surgical changes.

## 3. Build
- It must actually compile: `pio run`. Paste the real output.
- Warnings on the files you touched get read, not ignored.

## 4. Bench proof
- Compiling is not working. Nothing is "working" until it ran on the hardware.
- Prove state transitions with real logged data: heat the chamber, capture the
  serial trace, show the transition at the threshold and the hysteresis on the
  way back down.
- If it has not been run on hardware, say exactly that. Do not imply otherwise.

## 5. Electrical safety check
- Motor supply separate from the MCU rail, common ground.
- Level shifting present on any 5V I2C line.
- Buzzer and motor current not drawn through a GPIO.
- Confirm nothing added can brown out the board mid-demo.

## Rules
- Real measurements only. A number in the report must be one we actually took.
- Loud failure over silent default, always.
- Root causes, not symptom patches.
