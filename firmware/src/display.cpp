#include "display.h"

#include <cmath>
#include <cstdio>

void display_value(char* out, size_t n, float celsius) {
  if (std::isnan(celsius)) {
    snprintf(out, n, "--.-");
    return;
  }
  snprintf(out, n, "%.1f", celsius * 9.0f / 5.0f + 32.0f);
}

const char* display_state_text(VentState s) {
  switch (s) {
    case VentState::STANDBY: return "IDLE";
    case VentState::CROSS_VENT: return "CROSS VENT";
    case VentState::EXHAUST_ONLY: return "EXHAUST";
    case VentState::SEALED: return "SEALED";
    case VentState::FAULT: return "SENSOR FAULT";
  }
  return "?";
}

const char* display_state_long(VentState s) {
  switch (s) {
    case VentState::STANDBY: return "STANDBY";
    case VentState::CROSS_VENT: return "CROSS-VENT";
    case VentState::EXHAUST_ONLY: return "EXHAUST ONLY";
    case VentState::SEALED: return "SEALED";
    case VentState::FAULT: return "SENSOR FAULT";
  }
  return "?";
}

bool display_state_scrolls(VentState s) { return s == VentState::FAULT; }

char display_marker(bool simulated, bool manual) {
  if (simulated) return 'S';
  if (manual) return 'M';
  return 0;
}
