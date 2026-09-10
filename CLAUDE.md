# ESDL Project 1 — Automated Warehouse Ventilation System

**Course:** ESDL (Electrical System Design Lab) — Tennessee State University, ECE
**Team:** TJ (Terrence Parham), Tabitha, Claude (designated ESDL specialist)
**Timeline:** 7-week project. Week 3 as of 2026-09-09 → ~4 weeks remain.

> This is a hardware / embedded C++ class project. It has NOTHING to do with the
> Howard trading ASI in ~/Projects/Howard_MoE. Different hat, different standards.

## Project Goal
Design and prototype a closed-loop, automated warehouse ventilation system using an
ESP32-S3 that independently monitors internal and external temperature and dynamically
drives a dual-fan exhaust/intake setup with no human intervention.

## Bill of Materials (design intent)
| Part | Role |
|---|---|
| ESP32-S3 | Controller (3.3V logic) |
| 2x DHT22 | Internal (chamber) + ambient (outside) temperature |
| I2C LCD 16x2 (HD44780 + PCF8574) | Live telemetry for the demo |
| Active piezo buzzer | Critical thermal-overload alarm |
| Dual-channel motor driver | Drives both fans |
| 2x 130-size brushed DC motor | Intake fan + exhaust fan |
| Transparent enclosure | Diagonal cross-ventilation wind tunnel |

## Core Objectives
1. **Hardware integration** — all peripherals on one ESP32-S3.
2. **Finite state logic** — C++ FSM, thermal ONLY. Humidity is read and deliberately
   discarded to keep the control loop streamlined and reliable.
3. **Data visualization** — real-time Inside Temp / Outside Temp / System State on the
   local I2C LCD, to prove state changes live during the physical presentation.
4. **Physical prototyping** — transparent box, diagonal wind tunnel: intake bottom-left,
   exhaust top-right. Demonstrate airflow manipulation under a dry heat source.

## State Machine (demonstration triggers)
| State | Entry condition | Intake | Exhaust | Buzzer | LCD |
|---|---|---|---|---|---|
| `STANDBY`      | T_in < 80F                       | OFF | OFF | off | `STATE: STANDBY`   |
| `CROSS_VENT`   | T_in > 80F AND T_out < T_in      | ON  | ON  | off | `STATE: CROSS-VENT`|
| `EXHAUST_ONLY` | T_in > 80F AND T_out > T_in      | OFF | ON  | ON  | `STATE: EXHAUST`   |
| `FAULT` (added)| N consecutive bad sensor reads   | OFF | ON  | pattern | `SENSOR FAULT` |

Rationale for EXHAUST_ONLY: negative pressure flushes the chamber without deliberately
importing hotter outside air. Buzzer signals critical thermal overload.

## Standing engineering constraints (decided — do not silently regress)
- **Hysteresis is mandatory.** ON at 80.0F / OFF at 77.0F + minimum state dwell (~10s).
  A bare `>` threshold chatters the fans on sensor noise.
- **Differential deadband.** DHT22 is +/-0.5C each, so T_in - T_out carries ~+/-1.8F of
  uncertainty. Outside must be >=2F cooler before we open the intake.
- **NaN is the dangerous failure.** DHT22 returns NaN on CRC failure and every
  comparison against NaN is false -> silently lands in STANDBY with the box cooking.
  Explicit FAULT state, loud, fail-safe to exhaust-on. Never a silent default.
- **An OFF fan is not a damper.** A stopped 130-motor prop is an open hole; exhaust
  suction pulls hot air straight through it. Fix with a passive backdraft flapper over
  the intake port (thin plastic sheet, one-way) or by reversing the intake motor.
- **Ambient sensor placement.** Keep it well clear of the top-right exhaust plume or it
  reads our own hot exhaust -> latches EXHAUST_ONLY forever (positive feedback loop).
  Shield the internal sensor from direct heat-gun IR so it reads air temp, not radiance.
- **LCD level shifting.** PCF8574 backpack runs 5V for HD44780 contrast; its pull-ups
  then hold SDA/SCL at 5V and ESP32-S3 GPIO is NOT 5V tolerant (3.6V abs max).
  Use a BSS138 bidirectional level shifter on SDA/SCL.
- **Motor power is separate.** Never off the 3.3V rail or USB-through-board; brushed
  inrush browns out the MCU mid-demo. Common ground. 0.1uF ceramic across each motor's
  terminals -- brush noise killing I2C is the #1 failure in this exact build.
- **Driver choice.** DRV8833 or TB6612FNG (native 3.3V logic). L298N is marginal
  (2.3V min input high) and drops ~2V across the bridge.
- **Buzzer drive.** Bare active buzzer element (~30mA) goes through an NPN, not straight
  off a GPIO (20mA recommended max). A buzzer *module* with onboard transistor is fine.
- **Pin selection.** Avoid strapping pins (0, 3, 45, 46), USB (19/20), and flash/PSRAM.
  GPIO 33-37 are UNUSABLE on S3 modules with octal PSRAM (N8R8). Safe: 4-18, 21.
- **Non-blocking only.** millis() cooperative scheduler, zero delay() in loop().
  DHT22 has a hard 2s minimum between reads -> poll 0.5Hz, staggered between sensors.
  LCD refresh 2Hz, rewrite only changed characters (full clear() every loop = flicker).
- **Units.** All control logic in Celsius (DHT22 native); convert only for display.
  80F = 26.67C.

## Work standards for this project
- Military-grade thoroughness, root causes not symptoms. No shortcuts.
- Real sensor data only. Loud failure if a reading is missing -- never a silent default.
- Never claim something works without proof of actual execution on hardware.
- Every claim in the report must be backed by a measurement we actually took.

## Layout
- `firmware/` -- ESP32-S3 C++ (Arduino framework / PlatformIO)
- `hardware/` -- schematic, pinout, BOM, enclosure drawings
- `docs/`     -- project brief, design docs, test plan, report drafts
- `test/`     -- bench test procedures and recorded results

## Open questions (blocking full design)
1. What parts are physically in hand? Exact ESP32-S3 board model (PSRAM variant matters).
2. What was completed in weeks 1-2 (proposal, schematic, BOM, breadboarding, code)?
3. Graded deliverables and due dates -- is there a lab handout / rubric?
4. Division of labor: TJ vs Tabitha vs Claude.
