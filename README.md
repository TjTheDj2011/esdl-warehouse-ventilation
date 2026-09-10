# ESDL Project 1 — Automated Warehouse Ventilation System

Closed-loop thermal ventilation controller on an ESP32-S3. Two DHT22 sensors
(chamber + ambient) drive a finite state machine that commands an intake and an
exhaust fan through a dual-channel motor driver, with live telemetry on an I2C LCD
and a piezo alarm on critical thermal overload.

Team: TJ, Tabitha, Claude. 7-week ESDL course project.

See `CLAUDE.md` for the full design brief, state machine, and standing engineering
constraints. See `docs/` for design documents and the test plan.

## Status
Week 3 of 7 — architecture defined, hardware inventory pending.
