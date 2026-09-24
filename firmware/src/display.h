// Display content for the three SSD1306 OLED panels.
//
//   panel 1  IN    chamber temperature, very large
//   panel 2  OUT   ambient temperature, very large
//   panel 3  STATE system state, large; scrolls only on FAULT
//
// This module produces only the STRINGS. Pixel rendering lives in main.cpp,
// which keeps the formatting rules provable on a host - the same reason the
// control law is isolated in control.cpp.
#pragma once

#include <cstddef>

#include "control.h"

// Panel geometry, for the renderer and for the width assertions in the tests.
constexpr int OLED_W = 128;
constexpr int OLED_H = 64;

// Longest value string is "-100.4" style; 8 gives headroom for the NUL.
constexpr size_t DISPLAY_FIELD_MAX = 8;

// Writes a Fahrenheit reading, or "--.-" when the reading is not trustworthy.
// A failed sensor must never render as a plausible number such as 0.0.
void display_value(char* out, size_t n, float celsius);

// Label for the big state panel. The renderer splits it at the SPACE and
// stacks the two halves when it will not fit on one line at a readable size,
// so a two-word label spells itself out instead of being abbreviated. The
// space is therefore load-bearing: each half must fit on its own line, which
// host check [12] enforces. Single words must stay within that limit too.
const char* display_state_text(VentState s);

// Longer wording for the serial trace and for reports, where width is free.
const char* display_state_long(VentState s);

// FAULT scrolls: motion draws the eye, which is what you want when something
// is wrong. The four normal states stay static, because a glancing reader
// takes in a still word far faster than a moving one.
bool display_state_scrolls(VentState s);

// Corner markers so a rig left in a bench mode is never mistaken for a live
// closed-loop run. Returns 0 when nothing should be shown.
char display_marker(bool simulated, bool manual);
