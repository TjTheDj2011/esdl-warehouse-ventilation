# Tinkercad Circuits Build Guide

A working simulation of the ventilation controller in Tinkercad Circuits.
Sketch: `firmware/tinkercad/esdl_vent_tinkercad.ino`

---

## What this is, and what it is not

**Tinkercad has no ESP32 and no DHT22.** It supports only the Arduino Uno R3,
ATtiny85 and micro:bit, and its temperature part is the analog TMP36. So this is
a port, not a mirror of the real build:

| Real build | Tinkercad | Consequence |
|---|---|---|
| ESP32-WROOM-32 | Arduino Uno R3 | 5 V logic, so **no level shifter needed** |
| 2x DHT22 (digital, ±0.5 °C) | 2x TMP36 (analog, ±2 °C) | far coarser; see limitations |
| DRV8833 | L293D | same H-bridge idea, bulkier chip |
| I2C LCD (PCF8574) | parallel 16x2 LCD | uses 6 pins instead of 2 |
| Active buzzer module | Piezo | same GPIO behaviour |

**The control law is identical.** Same five states, same thresholds, same
hysteresis, same fault handling. `test/tinkercad/run.sh` compiles the sketch
against a stubbed Arduino API and asserts it behaves the same as the ESP32
firmware — 16 checks, including the analog path.

---

## Parts to drag out

- Arduino Uno R3
- Breadboard (small is fine)
- 2x **TMP36** temperature sensor
- **L293D** motor driver IC
- 2x **DC Motor**
- **LCD 16x2** (the parallel one)
- **Piezo**
- **Potentiometer** 10 kΩ — LCD contrast. Without it the screen stays blank.
- **Resistor** 220 Ω — LCD backlight
- **9 V Battery** or battery pack — motor supply

---

## Wiring

### TMP36 sensors
Flat face toward you: **left = +5 V, middle = signal, right = GND.**
Getting these backwards makes the part heat up and read nonsense.

| Sensor | Middle pin goes to |
|---|---|
| TMP36 #1 — chamber / inside | **A0** |
| TMP36 #2 — ambient / outside | **A1** |

### LCD (parallel)
The data-pin numbering crosses over. Follow the table, not intuition.

| LCD pin | Connects to |
|---|---|
| VSS | GND |
| VDD | 5 V |
| V0 | potentiometer **wiper** (middle leg) |
| RS | Arduino **12** |
| RW | GND |
| E | Arduino **11** |
| D4 | Arduino **5** |
| D5 | Arduino **4** |
| D6 | Arduino **3** |
| D7 | Arduino **2** |
| A | 5 V through the 220 Ω resistor |
| K | GND |

Potentiometer outer legs go to 5 V and GND.

### L293D motor driver
Pin 1 is at the notch, counting anticlockwise.

| L293D pin | Name | Connects to |
|---|---|---|
| 1 | EN1,2 | 5 V |
| 2 | IN1 | Arduino **6** |
| 3 | OUT1 | Motor 1 terminal A |
| 4, 5 | GND | GND |
| 6 | OUT2 | Motor 1 terminal B |
| 7 | IN2 | Arduino **7** |
| 8 | VCC2 | **Battery +** (motor supply) |
| 9 | EN3,4 | 5 V |
| 10 | IN3 | Arduino **8** |
| 11 | OUT3 | Motor 2 terminal A |
| 12, 13 | GND | GND |
| 14 | OUT4 | Motor 2 terminal B |
| 15 | IN4 | Arduino **9** |
| 16 | VCC1 | 5 V |

Motor 1 = intake, Motor 2 = exhaust.

**Battery negative goes to the GND rail** — the same common-ground rule as the
real build, and the same failure if you skip it.

### Piezo
`+` to Arduino **10**, `-` to GND.

---

## Loading the code

Open **Code**, switch the dropdown from Blocks to **Text**, delete what is there
and paste the whole of `esdl_vent_tinkercad.ino`. Tinkercad accepts only one
file, which is why the sketch is self-contained rather than split into modules
like the real firmware.

Then press **Start Simulation**.

---

## Driving the demo

Click a TMP36 during simulation and drag its temperature slider.

| Inside | Outside | Expected state | Fans |
|---|---|---|---|
| 72 °F | 65 °F | `STANDBY` | both stopped |
| 85 °F | 65 °F | `CROSS_VENT` | both forward |
| 85 °F | 84 °F | `EXHAUST_ONLY` | intake **reversed**, exhaust forward |
| 85 °F | 95 °F | `SEALED` | both stopped, alarm on |
| 78 °F | 65 °F | still `CROSS_VENT` | hysteresis holds until 77 °F |

**Leave about 10 seconds between changes.** The minimum dwell deliberately
blocks faster transitions — that is the anti-chatter guard working, not a bug.

The sliders are in Celsius; 80 °F is 26.7 °C and 77 °F is 25.0 °C.

**To demonstrate FAULT:** drag the middle wire of one TMP36 off its pin and onto
GND. That reads about −50 °C, outside the sensor's valid range, and after three
consecutive bad reads the controller enters `FAULT` — exhaust still driven,
buzzer pattern running. It never falls silently into `STANDBY`.

Open the **Serial Monitor** (9600 baud) for the running state trace.

---

## Limitations to state honestly

If this simulation appears in the report, these belong with it:

1. **TMP36 is ±2 °C against the DHT22's ±0.5 °C.** The simulated sensors are
   four times less accurate than the real ones.
2. **The 10-bit ADC quantises to about 0.5 °C (0.9 °F) per step.** Our intake
   deadband is 2.0 °F, so the simulation can only just resolve it. The real
   build's digital DHT22 has no such problem.
3. **It proves sequencing, not physics.** The simulation shows the state machine
   transitions correctly. It says nothing about airflow, chamber cool-down rates,
   whether reversing the intake actually helps, or brush noise on the I2C bus —
   the things that decide whether the real thing works.
4. **No level shifter appears** because the Uno is 5 V. That is the single most
   important electrical detail of the real build, and the simulation cannot show
   it.

Use it to demonstrate the logic. Use the bench rig for evidence.
