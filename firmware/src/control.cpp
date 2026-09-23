#include "control.h"

#include <cmath>

namespace {
// DHT22 rated sensing range. A reading outside this is as untrustworthy as NaN.
constexpr float kSensorMinC = -40.0f;
constexpr float kSensorMaxC = 80.0f;

// Absolute temperature conversion.
constexpr float f_to_c(float f) { return (f - 32.0f) * 5.0f / 9.0f; }
// Temperature *difference* conversion. A delta has no 32-degree offset --
// converting one with f_to_c() is a classic and silent unit bug.
constexpr float f_delta_to_c(float df) { return df * 5.0f / 9.0f; }
}  // namespace

VentConfig default_vent_config() {
  VentConfig c;
  c.hot_on_c = f_to_c(80.0f);   // 26.67 C
  c.hot_off_c = f_to_c(77.0f);  // 25.00 C
  c.cross_enter_diff_c = f_delta_to_c(2.0f);  // 1.11 C, clears sensor stack-up
  c.cross_exit_diff_c = f_delta_to_c(1.0f);   // 0.56 C, release hysteresis
  c.seal_enter_diff_c = f_delta_to_c(-3.0f);  // outside 3 F hotter -> stop exchanging
  c.seal_exit_diff_c = f_delta_to_c(-1.5f);   // release hysteresis
  c.fault_streak = 3;
  c.min_dwell_ms = 10000;
  return c;
}

VentController::VentController(const VentConfig& cfg) : cfg_(cfg) {}

bool VentController::reading_valid(float c) const {
  return !std::isnan(c) && c >= kSensorMinC && c <= kSensorMaxC;
}

void VentController::update(uint32_t now_ms, float t_in_c, float t_out_c) {
  const bool first = !started_;
  if (first) {
    started_ = true;
    entered_ms_ = now_ms;
  }

  const bool in_ok = reading_valid(t_in_c);
  const bool out_ok = reading_valid(t_out_c);

  if (in_ok && out_ok) {
    fail_streak_ = 0;
  } else if (fail_streak_ < 255) {
    ++fail_streak_;
  }

  VentState desired;
  if (fail_streak_ >= cfg_.fault_streak) {
    // Fail loud and fail safe. Never a silent fall-through to STANDBY with the
    // chamber cooking -- every comparison against NaN is false, which is
    // precisely the trap this branch exists to avoid.
    desired = VentState::FAULT;
  } else {
    // Latches update only from trustworthy data. Below the fault threshold we
    // ride through a dropout on the last known-good decision.
    if (in_ok) {
      if (!hot_ && t_in_c >= cfg_.hot_on_c) {
        hot_ = true;
      } else if (hot_ && t_in_c <= cfg_.hot_off_c) {
        hot_ = false;
      }
    }
    if (in_ok && out_ok) {
      const float diff = t_in_c - t_out_c;
      if (!cross_ && diff >= cfg_.cross_enter_diff_c) {
        cross_ = true;
      } else if (cross_ && diff < cfg_.cross_exit_diff_c) {
        cross_ = false;
      }
      // Upper bound on exchange. Moving air only cools while the air we pull in
      // is not hotter than the air we push out.
      if (!seal_ && diff <= cfg_.seal_enter_diff_c) {
        seal_ = true;
      } else if (seal_ && diff > cfg_.seal_exit_diff_c) {
        seal_ = false;
      }
    }
    if (!hot_) {
      desired = VentState::STANDBY;
    } else if (seal_) {
      // Outside is meaningfully hotter. Any forced exchange imports heat, so
      // the least-bad action is no action. This cannot deadlock: an internal
      // heat source raises T_in until it passes T_out, which clears the latch
      // and resumes exhausting.
      desired = VentState::SEALED;
    } else if (cross_) {
      desired = VentState::CROSS_VENT;
    } else {
      desired = VentState::EXHAUST_ONLY;
    }
  }

  if (desired != state_) {
    // Dwell keeps the fans from hunting. A fault is a safety event and
    // preempts it; so does the very first decision after boot, so we do not
    // sit in STANDBY for 10 s with a hot box.
    const bool preempt = first || desired == VentState::FAULT;
    if (preempt || (now_ms - entered_ms_) >= cfg_.min_dwell_ms) {
      state_ = desired;
      entered_ms_ = now_ms;
    }
  }
}

VentOutputs VentController::outputs_for(VentState s) {
  switch (s) {
    case VentState::CROSS_VENT:
      // Outside air is meaningfully cooler, so drive a directed jet diagonally
      // across the chamber: in at bottom-left, out at top-right.
      return {FanDrive::FORWARD, FanDrive::FORWARD, BuzzerMode::OFF};

    case VentState::EXHAUST_ONLY:
      // Inside and outside are within a few degrees, so exchange is close to
      // thermally neutral and the win is removing internally generated heat.
      // The exhaust sits high where buoyant hot air collects, so it skims the
      // hottest layer; makeup air enters low through the idle intake fan.
      // That ingress is harmless here by construction: if outside were
      // meaningfully hotter we would be in SEALED, not this state.
      return {FanDrive::OFF, FanDrive::FORWARD, BuzzerMode::STEADY};

    case VentState::SEALED:
      // Both fans braked: stop importing heat we cannot remove. The alarm
      // sounds because the system is thermally cornered and a human should
      // know -- this is the one condition two fans cannot fix.
      return {FanDrive::OFF, FanDrive::OFF, BuzzerMode::STEADY};

    case VentState::FAULT:
      // Temperatures are untrustworthy. Exhausting bounds the chamber near
      // ambient; sealing would let an unattended heat source run away with no
      // bound at all. Bounded beats unbounded, so we flush. Distinct pattern.
      return {FanDrive::OFF, FanDrive::FORWARD, BuzzerMode::PATTERN};

    case VentState::STANDBY:
    default:
      return {FanDrive::OFF, FanDrive::OFF, BuzzerMode::OFF};
  }
}

void VentController::reset_latches() {
  hot_ = false;
  cross_ = false;
  seal_ = false;
  fail_streak_ = 0;
}

const char* VentController::fan_name(FanDrive d) {
  switch (d) {
    case FanDrive::OFF: return "off";
    case FanDrive::FORWARD: return "fwd";
    case FanDrive::REVERSE: return "rev";
    default: return "?";
  }
}

const char* VentController::state_name(VentState s) {
  switch (s) {
    case VentState::STANDBY: return "STANDBY";
    case VentState::CROSS_VENT: return "CROSS_VENT";
    case VentState::EXHAUST_ONLY: return "EXHAUST_ONLY";
    case VentState::SEALED: return "SEALED";
    case VentState::FAULT: return "FAULT";
    default: return "?";
  }
}
