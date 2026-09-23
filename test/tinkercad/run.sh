#!/usr/bin/env bash
# Prove the Tinkercad Arduino port behaves identically to the ESP32 firmware.
# Stubs the Arduino API so the .ino compiles and runs on a host.
set -euo pipefail
cd "$(dirname "$0")"
TMP="$(mktemp -d)"
cp Arduino.h LiquidCrystal.h test.cpp "$TMP/"
cp ../../firmware/tinkercad/esdl_vent_tinkercad.ino "$TMP/"
g++ -std=c++17 -Wall -I"$TMP" "$TMP/test.cpp" -o "$TMP/tctest"
"$TMP/tctest"
