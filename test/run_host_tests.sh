#!/usr/bin/env bash
# Build and run the host-side proof of the control law and display formatting.
# No hardware needed. Run from anywhere:  ./test/run_host_tests.sh
set -euo pipefail
cd "$(dirname "$0")/.."
OUT="$(mktemp -d)/vent_test"
g++ -std=c++17 -Wall -Wextra -I firmware/src \
    test/test_control_host.cpp firmware/src/control.cpp firmware/src/display.cpp \
    -o "$OUT"
"$OUT"
