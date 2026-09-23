# Control Matrix — Fan State vs Temperature

Authoritative behaviour table for the ventilation controller. The firmware is
tested against this document directly: `test_control_host.cpp` sections [13]-[17]
assert every row and every invariant below, so the code and this table cannot
silently drift apart.

## Governing principle

> **Move air only when the air we pull in is cooler than the air we push out.
> Otherwise, stop moving air.**

Everything below follows from that one rule. Two fans can only exchange chamber
air for outside air — so ventilation cools when outside is cooler, does nothing
useful when they are equal, and actively *heats* when outside is hotter. A
controller that ventilates unconditionally is not a cooling system; it is a
machine for dragging the interior toward ambient in whichever direction ambient
happens to lie.

### Physical limit, stated plainly

**This system cannot cool below outside temperature.** There is no refrigeration
in the design — only air exchange. The honest claim for the report is:

> The controller drives the chamber toward the lowest temperature obtainable by
> air exchange, and never takes an action that makes the chamber hotter.

Claiming it "keeps the warehouse cool regardless of conditions" would not survive
a question, because on a 110F day with 85F inside, the correct action is to do
nothing and sound an alarm.

## Inputs

| Input | Source | Used in control? |
|---|---|---|
| `T_in` — chamber temperature | DHT22, GPIO 4 | **Yes** |
| `T_out` — ambient temperature | DHT22, GPIO 16 | **Yes** |
| Relative humidity, both sensors | same DHT22 transaction | **No** — diagnostics only |

Thermal only. Humidity arrives free in the same bus transaction and is logged to
show sensor health, but never reaches a decision.

## Fan direction convention

| Fan | Position | ON | OFF |
|---|---|---|---|
| Intake | low, one wall | air **into** chamber | stopped - becomes a passive vent |
| Exhaust | high, opposite wall | air **out of** chamber | stopped |

**Both fans are brushless and run one direction only.** No state ever reverses
a fan, and test [13] asserts it. `REVERSE` still exists in the firmware because
the H-bridge can do it and the bring-up console uses it to prove both
half-bridges are wired, but automatic control never emits it.

## The matrix

Let `D = T_in − T_out`. Positive `D` means the chamber is hotter than outside.

| # | Sensors | Chamber | `D` | State | Intake | Exhaust | Buzzer |
|---|---|---|---|---|---|---|---|
| 1 | valid | below 77.0F | any | `STANDBY` | OFF | OFF | off |
| 2 | valid | 77.0–80.0F | any | *latched* — holds previous state | | | |
| 3 | valid | above 80.0F | `D ≥ +2.0F` | `CROSS_VENT` | **ON** | ON | off |
| 4 | valid | above 80.0F | `−3.0F < D < +2.0F` | `EXHAUST_ONLY` | **OFF** | ON | steady |
| 5 | valid | above 80.0F | `D ≤ −3.0F` | `SEALED` | **OFF** | **OFF** | steady |
| 6 | 3 bad reads | unknown | unknown | `FAULT` | **OFF** | ON | 4 Hz pattern |

Row 2 is the hysteresis band. Rows 3–5 each release on a narrower figure than
they engage on (`+1.0F` and `−1.5F` respectively). Every transition also
requires 10 s minimum dwell.

## Airflow paths

```
  STANDBY / SEALED           CROSS_VENT                 EXHAUST_ONLY / FAULT

      [exhaust]                  [exhaust]==>               [exhaust]==>
  +---------------+          +---------------+          +---------------+
  |               |          |          ,----|          |          ,---'|
  |    chamber    |          |      ,--'     |          |     ,---'     |
  |               |          |  ,--'         |          | ,--'          |
  +---------------+          +---------------+          +---------------+
     [intake]                   ==>[intake]               ==>[intake]
      stopped                      driven                   stopped, but
                                                            air is drawn IN
                                                            through it
```

## Why each state

**`STANDBY` — both stopped.** Below setpoint there is nothing to do. The idle
fans still form two small openings, so slow passive exchange continues; that is
acceptable here because the chamber is already below setpoint.

**`CROSS_VENT` — both forward.** Outside air is meaningfully cooler, so it is
worth deliberately importing. The intake drives a directed jet diagonally across
the chamber to the exhaust — the most efficient heat-transport geometry two fans
can produce.

**`EXHAUST_ONLY` — exhaust alone.** Inside and outside are within a few degrees
of each other. Exchange is close to thermally neutral, so the win comes from
removing heat the chamber generates internally. The exhaust sits high on the
opposite wall where buoyant hot air collects, so it skims the hottest stratified
layer. Makeup air is drawn in low through the **idle intake fan** — exactly where
we want it to enter.

That ingress is safe *by construction*, and this is the part worth understanding.
The earlier design reversed the intake specifically to block backdraft, because a
stopped fan is an open hole. But air only comes through that hole while the
exhaust runs, and in this state the exhaust only runs when outside is within 3F.
If outside were meaningfully hotter we would be in `SEALED` with both fans
stopped. **Adding `SEALED` removed the reason the reversal existed**, which is
what allowed the design to drop to one-directional brushless fans.

**`SEALED` — both stopped, alarm on.** Outside is meaningfully hotter. Every cubic
metre exchanged would make the chamber worse, so the correct action is none. The
alarm sounds because this is the one condition two fans cannot fix and a human
needs to know — open a different door, wait for nightfall, or add real cooling.

**`FAULT` — flush, distinct pattern.** Temperatures are untrustworthy. Exhausting
bounds the chamber near ambient; sealing would let an unattended heat source run
away with no bound at all. **Bounded beats unbounded**, so a fault flushes.

## Two properties worth defending out loud

**1. `SEALED` cannot deadlock.** The obvious objection is that sealing a box with
a heat source in it just lets the box cook. It does not, and the reason is
structural rather than a special case in the code: while sealed, the internal
source raises `T_in`. As `T_in` climbs past `T_out`, `D` turns positive, the seal
latch releases, and ventilation resumes on its own. The system physically cannot
get stuck cooking. Test [15] demonstrates this.

**2. No state ever forces exchange with hotter air.** Test [17] sweeps outside
temperature from 60F to 130F against a 95F chamber and asserts that beyond the
seal point no fan is ever driven. This is the governing principle expressed as an
executable check rather than a claim.

## Guard rails

**Hysteresis — 80.0F on, 77.0F off.** A bare threshold chatters the fans on
sensor noise. Inside the 3F band, the previous state holds.

**Differential deadband — 2.0F to open the intake, 1.0F to release.** Each DHT22
is ±0.5C, so `D` carries roughly ±1.0C (±1.8F) of uncertainty. Requiring 2.0F
means we never act on noise.

**Seal threshold — 3.0F to seal, 1.5F to release.** Also chosen to clear the
±1.8F stack-up, so the system only seals when outside is genuinely hotter rather
than apparently hotter. **This value is a defensible starting point, not a
measured one** — see below.

**Minimum dwell — 10 s.** Caps how fast the system changes its mind, so a
transient cannot produce visible hunting during the demo.

**Fault threshold — 3 consecutive bad reads (~7.5 s).** Tolerates the occasional
CRC failure a DHT22 normally produces, while still reacting to a real failure.

## What still needs measuring

This table specifies intent. None of it is verified on hardware yet. To back it:

- [ ] Serial trace of every transition under real heat, with timestamps
- [ ] **The seal threshold.** 3.0F is reasoned, not measured. Determine the real
      crossover by holding the chamber at a fixed temperature, sweeping outside
      temperature, and finding where forced exchange stops helping.
- [ ] Airflow through the idle intake fan in `EXHAUST_ONLY` — confirm the exhaust
      is not stalling against its own negative pressure and that makeup air
      genuinely enters low
- [ ] Blocking the idle intake fan in `EXHAUST_ONLY` vs leaving it open —
      cool-down curves for both, to prove the makeup path matters
- [ ] Confirmation the ambient sensor never reads the exhaust plume

Until those exist, everything here is design intent, not a result.
