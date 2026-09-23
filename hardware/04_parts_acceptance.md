# Parts Acceptance Card

For the supply room. What to take, what to substitute, what to refuse.
Full list in `03_physical_build.md`.

---

## Two substitutions that BREAK the design

### 1. DHT11 instead of DHT22 — refuse if you can

Lab kits are full of DHT11 (blue). We need **DHT22 / AM2302** (white).

| | DHT22 | DHT11 |
|---|---|---|
| Accuracy | ±0.5 °C | **±2 °C** |
| Resolution | 0.1 °C | **1 °C** |
| Range | −40 to 80 °C | 0 to 50 °C |

Our whole differential design rests on DHT22 accuracy. Two DHT22s give
`T_in − T_out` about ±1.8 °F of uncertainty, which is why the intake deadband is
2.0 °F. **Two DHT11s give roughly ±7.2 °F of uncertainty** — larger than every
threshold we have. The controller could not tell a real 3 °F difference from
noise, and `CROSS_VENT` / `EXHAUST_ONLY` / `SEALED` would become guesswork.

If DHT11 is genuinely all there is: take it, tell Claude, and we widen every
differential threshold to ~8 °F and document the accuracy hit as a known
limitation. The design still runs, but the thresholds stop being defensible and
the 1 °C resolution will make the LCD look coarse.

### 2. Brushless PC fans instead of brushed motors — refuse

A 40 mm or 80 mm PC case fan looks like an upgrade: quieter, no brush noise, easy
to mount, no soldering. **But a 2- or 3-wire brushless fan cannot run backwards.**
Its commutation is one-directional by design, and reversing supply polarity just
stops it (or damages it).

Our `EXHAUST_ONLY` and `FAULT` states **reverse the intake fan**. That requires a
**brushed DC motor** on an H-bridge. Keep the 130-size motors.

Worth taking anyway if offered free: a brushless fan makes a fine external heat
extractor for the bench, and it proves out mounting geometry.

---

## Happy substitutions — take these

| If offered | Verdict |
|---|---|
| **TB6612FNG** driver | **Better than DRV8833.** Needs 7 GPIO (AIN1/2, PWMA, BIN1/2, PWMB, STBY) instead of 5. We have spare pins. Take it. |
| **L298N** driver | **Take it if it is free.** I advised against *buying* one, and that still stands — but free changes the maths. 3.3 V clears its 2.3 V logic-high threshold, and its ~2 V drop still leaves ~4 V from a 6 V pack, which is plenty for a 3 V-rated 130 motor. Bulky and wasteful, not broken. |
| **20x4 LCD** with I2C backpack | Take it — strictly better. Two-line change in `display.h`, and the extra width finally fits `STATE: CROSS-VENT` in full. |
| **Bench power supply** | Take it. Better than a battery pack: adjustable, current-limited, will not go flat mid-demo. Set 5–6 V for the motors. |
| **Breadboard power supply module** | Useful, but **only for logic**. Motors still need their own supply. |
| **Any 2N2222 / 2N3904 NPN + 1k resistor** | Grab a few. Needed if the buzzer is a bare element rather than a module. |

---

## Ask carefully about these

**LCD — needs the I2C backpack.** A bare HD44780 with 16 pins and no backpack
needs 6 GPIO and 5 V level shifting on all six lines. Painful but survivable. Ask
if they have a **PCF8574 backpack module** separately — it solders straight on.

**Level shifter.** If they have no BSS138 module, try the LCD on **3.3 V first**.
Many PCF8574 backpacks run fine at 3.3 V with the contrast trimmer turned up, and
at 3.3 V there is no level problem at all. If contrast is unreadable, we need the
shifter. Do **not** connect a 5 V-powered backpack to the ESP32 without one.

**Buzzer.** Module with onboard transistor is ideal. A bare element needs the NPN
above — a GPIO should not source its ~30 mA directly.

**Heat source.** A lab heat gun is usually far too aggressive and will melt a
plastic tub. A hair dryer is the better tool here.

---

## Also worth asking for

- Soldering iron access — required for motor leads and the 0.1 uF caps
- **0.1 uF (100 nF) ceramic caps** — any lab has a drawer of these
- Hookup wire, heat-shrink, zip ties
- Digital thermometer or thermocouple — **independent verification of the DHT22
  readings**. Being able to say "we checked our sensors against a reference" is
  worth real marks.
- Clear plastic project box or sheet stock

---

## The one-line version

**Say yes to:** DHT22, any H-bridge, any I2C LCD, bench supply, caps, NPNs,
a reference thermometer.
**Push back on:** DHT11, brushless fans, a bare HD44780 with no backpack.
