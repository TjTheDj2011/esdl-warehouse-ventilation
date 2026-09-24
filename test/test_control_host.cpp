// Host-side proof of the ventilation control law. No hardware required.
//   g++ -std=c++17 -I firmware/src test/test_control_host.cpp
//       firmware/src/control.cpp firmware/src/display.cpp -o /tmp/vent_test
#include "control.h"
#include "display.h"

#include <cmath>
#include <cstdio>
#include <cstring>
#include <initializer_list>
#include <limits>

namespace {

int checks = 0;
int failures = 0;

constexpr float F(float f) { return (f - 32.0f) * 5.0f / 9.0f; }
const float NaNf = std::numeric_limits<float>::quiet_NaN();

const char* buzz(BuzzerMode m) {
  return m == BuzzerMode::OFF ? "off" : (m == BuzzerMode::STEADY ? "STEADY" : "PATTERN");
}

class Rig {
 public:
  Rig() : c_(default_vent_config()) {}

  // Advance the clock and feed one sensor pair. Inputs in Fahrenheit for
  // readability; the controller works in Celsius.
  void step(uint32_t dt_ms, float in_f, float out_f) {
    now_ += dt_ms;
    c_.update(now_, std::isnan(in_f) ? in_f : F(in_f),
              std::isnan(out_f) ? out_f : F(out_f));
  }
  void hold(uint32_t total_ms, float in_f, float out_f) {
    for (uint32_t t = 0; t < total_ms; t += 2500) step(2500, in_f, out_f);
  }
  VentState state() const { return c_.state(); }
  void reset() { c_.reset_latches(); }
  VentOutputs out() const { return c_.outputs(); }
  uint32_t now() const { return now_; }

 private:
  VentController c_;
  uint32_t now_ = 0;
};

void check(bool ok, const char* what, const Rig& r) {
  ++checks;
  if (!ok) ++failures;
  VentOutputs o = r.out();
  std::printf("  [%s] t=%6ums %-13s intake=%-3s exhaust=%-3s buzzer=%-7s  %s\n",
              ok ? "PASS" : "FAIL", r.now(), VentController::state_name(r.state()),
              VentController::fan_name(o.intake),
              VentController::fan_name(o.exhaust), buzz(o.buzzer), what);
}

}  // namespace

int main() {
  std::printf("\n=== ESDL Project 1 :: ventilation control law, host proof ===\n");
  std::printf("Thresholds: hot ON 80.0F / OFF 77.0F, intake deadband 2.0F,\n"
              "            fault after 3 bad reads, min dwell 10 s\n");

  {
    std::printf("\n[1] Cold chamber holds STANDBY, both fans off\n");
    Rig r;
    r.hold(30000, 72.0f, 68.0f);
    check(r.state() == VentState::STANDBY, "72F inside stays STANDBY", r);
    check(r.out().intake == FanDrive::OFF && r.out().exhaust == FanDrive::OFF,
          "both fans off", r);
  }

  {
    std::printf("\n[2] 79F does not trip the 80F threshold\n");
    Rig r;
    r.hold(30000, 79.0f, 60.0f);
    check(r.state() == VentState::STANDBY, "79F is below setpoint", r);
  }

  {
    std::printf("\n[3] Hot chamber, cool outside -> CROSS_VENT\n");
    Rig r;
    r.hold(15000, 72.0f, 65.0f);
    r.hold(20000, 82.0f, 65.0f);
    check(r.state() == VentState::CROSS_VENT, "82F in / 65F out opens intake", r);
    check(r.out().intake == FanDrive::FORWARD &&
              r.out().exhaust == FanDrive::FORWARD,
          "both fans forward: directed jet across the chamber", r);
    check(r.out().buzzer == BuzzerMode::OFF, "no alarm, this is nominal", r);
  }

  {
    std::printf("\n[4] Sensor noise across the setpoint must not chatter\n");
    Rig r;
    r.hold(20000, 82.0f, 65.0f);
    bool stayed = true;
    for (int i = 0; i < 12; ++i) {
      r.step(2500, (i % 2) ? 79.4f : 80.6f, 65.0f);  // +/-0.6F dither
      if (r.state() != VentState::CROSS_VENT) stayed = false;
    }
    check(stayed, "dither 79.4<->80.6F never drops out (hysteresis holds)", r);
  }

  {
    std::printf("\n[5] Outside SLIGHTLY hotter -> EXHAUST_ONLY + alarm\n");
    std::printf("    (outside much hotter is a different state -- see [14])\n");
    Rig r;
    r.hold(20000, 82.0f, 65.0f);
    r.hold(20000, 82.0f, 84.0f);  // 2F hotter: still worth flushing internal heat
    check(r.state() == VentState::EXHAUST_ONLY,
          "84F outside: close enough that flushing still pays", r);
    check(r.out().intake == FanDrive::OFF &&
              r.out().exhaust == FanDrive::FORWARD,
          "intake stops, exhaust runs: makeup air enters through the idle fan", r);
    check(r.out().buzzer == BuzzerMode::OFF,
          "no standing tone: sensors are good, entry chirp announces it", r);
  }

  {
    std::printf("\n[6] Marginal 1.5F differential is inside the deadband\n");
    Rig r;
    r.hold(20000, 82.0f, 84.0f);          // settle in EXHAUST_ONLY
    r.hold(20000, 82.0f, 80.5f);          // only 1.5F cooler outside
    check(r.state() == VentState::EXHAUST_ONLY,
          "1.5F < 2.0F deadband, intake stays shut", r);
  }

  {
    std::printf("\n[7] NaN handling: ride through, then fail loud and safe\n");
    Rig r;
    r.hold(20000, 82.0f, 65.0f);
    check(r.state() == VentState::CROSS_VENT, "established CROSS_VENT", r);
    r.step(2500, NaNf, 65.0f);
    r.step(2500, NaNf, 65.0f);
    check(r.state() == VentState::CROSS_VENT, "2 bad reads ride through", r);
    r.step(2500, NaNf, 65.0f);
    check(r.state() == VentState::FAULT, "3rd bad read declares FAULT", r);
    check(r.out().exhaust == FanDrive::FORWARD,
          "FAULT fails SAFE: exhaust stays driven", r);
    check(r.out().intake == FanDrive::OFF,
          "intake stopped; exhaust alone bounds the chamber near ambient", r);
    check(r.out().buzzer == BuzzerMode::STEADY,
          "continuous tone: the only state that cannot trust its sensors", r);
  }

  {
    std::printf("\n[8] The NaN trap: cooking box must never read as STANDBY\n");
    Rig r;
    r.hold(60000, NaNf, NaNf);
    check(r.state() != VentState::STANDBY,
          "all-NaN never silently lands in STANDBY", r);
    check(r.state() == VentState::FAULT, "it lands in FAULT instead", r);
  }

  {
    std::printf("\n[9] Recovery once the sensor comes back\n");
    Rig r;
    r.hold(20000, 82.0f, 65.0f);
    r.hold(15000, NaNf, 65.0f);
    check(r.state() == VentState::FAULT, "in FAULT", r);
    r.hold(20000, 82.0f, 65.0f);
    check(r.state() == VentState::CROSS_VENT, "good reads restore control", r);
  }

  {
    std::printf("\n[10] Cool-down releases only below 77F, not at 79F\n");
    Rig r;
    r.hold(20000, 82.0f, 65.0f);
    r.hold(20000, 78.5f, 65.0f);
    check(r.state() == VentState::CROSS_VENT, "78.5F still above OFF point", r);
    r.hold(20000, 76.0f, 65.0f);
    check(r.state() == VentState::STANDBY, "76F releases to STANDBY", r);
    check(r.out().intake == FanDrive::OFF && r.out().exhaust == FanDrive::OFF,
          "fans stop (braked)", r);
  }

  {
    std::printf("\n[11] Minimum dwell blocks immediate re-transition\n");
    Rig r;
    r.hold(20000, 72.0f, 65.0f);
    r.step(2500, 85.0f, 65.0f);
    VentState first = r.state();
    r.step(2500, 72.0f, 65.0f);
    check(r.state() == first, "state cannot flip again inside 10 s dwell", r);
  }

  {
    std::printf("\n[12] OLED panel content\n");
    struct Case { float in_c, out_c; const char* what; };
    const Case cases[] = {
        {F(72.0f), F(65.0f), "nominal"},
        {F(105.3f), F(101.2f), "both above 100F (heat-gun range)"},
        {F(176.0f), F(176.0f), "DHT22 maximum, 176F"},
        {F(-40.0f), F(-40.0f), "DHT22 minimum, -40F"},
        {NaNf, NaNf, "both sensors failed"},
        {F(82.0f), NaNf, "one sensor failed"},
    };
    Rig r;

    // The value panels draw one number very large, so the string has to stay
    // short enough to fit 128 px at that size. Six characters is the budget.
    bool fits = true;
    for (const Case& c : cases) {
      char v[DISPLAY_FIELD_MAX];
      display_value(v, sizeof(v), c.in_c);
      if (std::strlen(v) > 6) fits = false;
      display_value(v, sizeof(v), c.out_c);
      if (std::strlen(v) > 6) fits = false;
    }
    check(fits, "every reading renders in 6 characters or fewer", r);

    char v[DISPLAY_FIELD_MAX];
    display_value(v, sizeof(v), NaNf);
    check(std::strcmp(v, "--.-") == 0,
          "a failed read shows --.- and never a plausible 0.0", r);
    display_value(v, sizeof(v), F(80.4f));
    check(std::strcmp(v, "80.4") == 0, "80.4 F renders as \"80.4\"", r);

    const VentState states[] = {VentState::STANDBY, VentState::CROSS_VENT,
                                VentState::EXHAUST_ONLY, VentState::SEALED,
                                VentState::FAULT};
    bool labelled = true, scroll_only_fault = true;
    for (VentState st : states) {
      if (display_state_text(st)[0] == '\0') labelled = false;
      if (display_state_text(st)[0] == '?') labelled = false;
      if (display_state_long(st)[0] == '?') labelled = false;
      const bool scrolls = display_state_scrolls(st);
      if ((st == VentState::FAULT) != scrolls) scroll_only_fault = false;
    }
    check(labelled, "every state has a short and a long label", r);

    // The renderer stacks a label at its space, so each half is drawn on its
    // own line. At text size 3 - the smallest that reads across a room - a
    // character is 6*3 px wide, giving 128/18 = 7 characters per line. A label
    // whose word exceeds that is silently shrunk until it cannot be read, so
    // it is caught here rather than on the bench the night before a demo.
    bool label_fits = true;
    const char* oversize = "";
    for (VentState st : states) {
      const char* txt = display_state_text(st);
      const char* sp = std::strchr(txt, ' ');
      const size_t head = sp ? static_cast<size_t>(sp - txt) : std::strlen(txt);
      const size_t tail = sp ? std::strlen(sp + 1) : 0;
      if (head > 7 || tail > 7) { label_fits = false; oversize = txt; }
    }
    check(label_fits, label_fits
              ? "every label word fits one line at a readable size"
              : oversize, r);
    check(scroll_only_fault,
          "only FAULT scrolls - static text reads faster at a glance", r);

    check(display_marker(true, false) == 'S', "simulated input raises S", r);
    check(display_marker(false, true) == 'M', "manual override raises M", r);
    check(display_marker(false, false) == 0, "no marker during a live run", r);

    std::printf("       IN panel: \"%s\"    STATE panel: \"%s\"\n",
                (display_value(v, sizeof(v), F(80.4f)), v),
                display_state_text(VentState::CROSS_VENT));
  }

  {
    std::printf("\n[13] Fan-direction matrix matches the design table\n");
    Rig r;
    struct Row { VentState st; FanDrive intake, exhaust; const char* what; };
    const Row rows[] = {
        {VentState::STANDBY, FanDrive::OFF, FanDrive::OFF,
         "STANDBY      -> both braked"},
        {VentState::CROSS_VENT, FanDrive::FORWARD, FanDrive::FORWARD,
         "CROSS_VENT   -> intake fwd, exhaust fwd"},
        {VentState::EXHAUST_ONLY, FanDrive::OFF, FanDrive::FORWARD,
         "EXHAUST_ONLY -> intake off, exhaust fwd"},
        {VentState::SEALED, FanDrive::OFF, FanDrive::OFF,
         "SEALED       -> both braked, no exchange"},
        {VentState::FAULT, FanDrive::OFF, FanDrive::FORWARD,
         "FAULT        -> intake off, exhaust fwd"},
    };
    for (const Row& row : rows) {
      const VentOutputs o = VentController::outputs_for(row.st);
      check(o.intake == row.intake && o.exhaust == row.exhaust, row.what, r);
    }
    // No state may ever drive the intake inward while the outside is the
    // hotter side -- that is the whole point of the deadband.
    const VentOutputs eo = VentController::outputs_for(VentState::EXHAUST_ONLY);
    check(eo.intake != FanDrive::FORWARD,
          "intake never blows inward when outside is not cooler", r);
    // Brushless fans cannot reverse. Automatic control must never ask.
    bool never_reversed = true;
    for (VentState st : {VentState::STANDBY, VentState::CROSS_VENT,
                         VentState::EXHAUST_ONLY, VentState::SEALED,
                         VentState::FAULT}) {
      const VentOutputs o = VentController::outputs_for(st);
      if (o.intake == FanDrive::REVERSE || o.exhaust == FanDrive::REVERSE)
        never_reversed = false;
    }
    check(never_reversed,
          "no state ever commands REVERSE - brushless fans cannot do it", r);
  }

  {
    std::printf("\n[14] Outside much hotter: the system must not import heat\n");
    Rig r;
    r.hold(20000, 85.0f, 110.0f);
    check(r.state() == VentState::SEALED,
          "85F in / 110F out seals instead of ventilating", r);
    check(r.out().intake == FanDrive::OFF && r.out().exhaust == FanDrive::OFF,
          "both fans braked: zero forced exchange with hotter air", r);
    check(r.out().buzzer == BuzzerMode::OFF,
          "cornered but not broken: chirp on entry, no standing tone", r);
  }

  {
    std::printf("\n[15] Sealing cannot deadlock (self-correcting)\n");
    Rig r;
    r.hold(20000, 85.0f, 110.0f);
    check(r.state() == VentState::SEALED, "sealed with outside hotter", r);
    // An internal heat source keeps working while we are sealed, so the
    // chamber climbs. Once it passes outside, exchanging pays off again.
    r.hold(20000, 111.0f, 110.0f);
    check(r.state() != VentState::SEALED,
          "chamber passing outside temp releases the seal", r);
    check(r.state() == VentState::EXHAUST_ONLY,
          "ventilation resumes automatically -- no stuck-cooking state", r);
  }

  {
    std::printf("\n[16] Seal boundary has hysteresis, not a bare threshold\n");
    Rig r;
    r.hold(20000, 85.0f, 87.0f);   // outside 2F hotter: inside the band
    check(r.state() == VentState::EXHAUST_ONLY,
          "outside only 2F hotter still flushes internal heat", r);
    r.hold(20000, 85.0f, 89.0f);   // outside 4F hotter: past the seal point
    check(r.state() == VentState::SEALED, "outside 4F hotter seals", r);
    r.hold(20000, 85.0f, 87.0f);   // back to 2F: inside the release band
    check(r.state() == VentState::SEALED,
          "does not immediately unseal at 2F (hysteresis holds)", r);
    r.hold(20000, 85.0f, 85.5f);
    check(r.state() == VentState::EXHAUST_ONLY, "clears once genuinely close", r);
  }

  {
    std::printf("\n[17] Governing invariant: never force exchange with hotter air\n");
    bool violated = false;
    for (int out_f = 60; out_f <= 130; ++out_f) {
      Rig r;
      r.hold(25000, 95.0f, static_cast<float>(out_f));
      const VentOutputs o = r.out();
      const bool exchanging =
          o.intake != FanDrive::OFF || o.exhaust != FanDrive::OFF;
      // 3F seal threshold + 1.8F sensor stack-up: beyond 99F outside there is
      // no defensible reason to be moving air.
      if (out_f > 99 && exchanging) violated = true;
    }
    Rig r;
    check(!violated,
          "swept outside 60-130F at 95F inside: no exchange once outside wins", r);
  }

  {
    std::printf("\n[18] Leaving simulation must not strand a latched state\n");
    Rig r;
    r.hold(25000, 85.0f, 65.0f);
    check(r.state() == VentState::CROSS_VENT, "hot latch set at 85F", r);
    // 77.6F sits inside the 77-80 hysteresis band, so the latch would hold.
    r.hold(25000, 77.6f, 65.0f);
    check(r.state() == VentState::CROSS_VENT,
          "77.6F alone keeps venting - hysteresis working as designed", r);
    // Clearing the latches is what leaving simulation must do.
    r.reset();
    r.hold(25000, 77.6f, 65.0f);
    check(r.state() == VentState::STANDBY,
          "after reset, 77.6F settles to STANDBY as a fresh boot would", r);
  }

  std::printf("\n=== %d checks, %d failures ===\n\n", checks, failures);
  return failures == 0 ? 0 : 1;
}
