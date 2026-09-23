// Thermal ventilation control FSM.
//
// Deliberately free of Arduino dependencies so it compiles and runs on a host
// machine. The control law is provable on the bench before hardware exists.
// All temperatures are Celsius -- see CLAUDE.md, "Units".
#pragma once

#include <cstdint>

enum class VentState : uint8_t {
  STANDBY = 0,
  CROSS_VENT,
  EXHAUST_ONLY,
  SEALED,
  FAULT,
};

// Fans are brushless and run one direction only, so automatic control never
// emits REVERSE. It is retained because the H-bridge can still do it and the
// bring-up console uses it to prove both half-bridges are wired correctly.
// FORWARD always means "the direction this fan was mounted to move air":
// into the chamber for the intake, out of it for the exhaust.
enum class FanDrive : uint8_t {
  OFF = 0,   // braked -- shorts the winding, resisting backdraft windmilling
  FORWARD,
  REVERSE,
};

enum class BuzzerMode : uint8_t {
  OFF = 0,
  STEADY,   // critical thermal overload (EXHAUST_ONLY)
  PATTERN,  // sensor fault, intermittent
};

struct VentOutputs {
  FanDrive intake;
  FanDrive exhaust;
  BuzzerMode buzzer;
};

struct VentConfig {
  // Chamber temperature hysteresis band. ON above hot_on, OFF below hot_off.
  // A bare '>' compare chatters the fans on sensor noise.
  float hot_on_c;
  float hot_off_c;

  // Differential deadband on (T_in - T_out). Each DHT22 is +/-0.5C, so the
  // difference carries ~1.0C of uncertainty; outside must be meaningfully
  // cooler before we open the intake. Second, narrower value gives the
  // CROSS_VENT <-> EXHAUST_ONLY boundary its own hysteresis.
  float cross_enter_diff_c;
  float cross_exit_diff_c;

  // Upper bound on air exchange. Once outside is this much HOTTER than inside,
  // ventilating imports heat faster than it removes it, so the system seals.
  // Without this bound the controller happily heats the space it is meant to
  // cool. Determine the final value by measurement -- see docs/03_control_matrix.md.
  float seal_enter_diff_c;  // negative: T_in - T_out at or below this seals
  float seal_exit_diff_c;   // negative: rises above this to resume exhausting

  // Consecutive bad reads (NaN / out-of-range) before declaring FAULT.
  uint8_t fault_streak;

  // Minimum time in a state before another transition is allowed.
  uint32_t min_dwell_ms;
};

VentConfig default_vent_config();

class VentController {
 public:
  explicit VentController(const VentConfig& cfg);

  // Feed the latest sensor pair. NaN is an expected input, not an error:
  // it means the DHT22 failed CRC. Safe to call at any rate.
  void update(uint32_t now_ms, float t_in_c, float t_out_c);

  VentState state() const { return state_; }
  VentOutputs outputs() const { return outputs_for(state_); }

  // Introspection, for the serial trace and the test harness.
  bool hot_latched() const { return hot_; }
  bool cross_latched() const { return cross_; }
  bool seal_latched() const { return seal_; }
  uint8_t fail_streak() const { return fail_streak_; }
  uint32_t ms_in_state(uint32_t now_ms) const { return now_ms - entered_ms_; }

  // Clear the latched decisions so the next update re-derives them from live
  // data. Needed when leaving simulation: hysteresis deliberately holds a
  // latch inside the band, so a rehearsal at 85F can leave the rig venting at
  // 77.6F - a state the real temperature never would have produced.
  void reset_latches();

  static const char* state_name(VentState s);
  static const char* fan_name(FanDrive d);
  static VentOutputs outputs_for(VentState s);

 private:
  bool reading_valid(float c) const;

  VentConfig cfg_;
  VentState state_ = VentState::STANDBY;
  bool hot_ = false;    // latched chamber-is-hot, with hysteresis
  bool cross_ = false;  // latched outside-is-cooler, with hysteresis
  bool seal_ = false;   // latched outside-is-much-hotter, with hysteresis
  uint8_t fail_streak_ = 0;
  uint32_t entered_ms_ = 0;
  bool started_ = false;
};
