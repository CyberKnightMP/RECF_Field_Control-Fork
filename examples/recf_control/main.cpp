#include "main.h"
// This diagnostic moves no motors and requires no display library.
static void show(const char *mode) {
    pros::screen::print(pros::E_TEXT_LARGE, 3, "%-24s", mode);
}
void initialize() {
    pros::c::recf_control_enable(true);
    pros::screen::print(pros::E_TEXT_MEDIUM, 1, "RECF_Control_State ready");
}
void disabled() { show("STOP"); }
void competition_initialize() { show("FIELD CONNECTED"); }
void autonomous() {
    show("AUTONOMOUS");
    // Replace this loop with your autonomous routine. Each new entry restarts it.
    while (pros::competition::is_autonomous() && !pros::competition::is_disabled()) pros::delay(20);
}
void opcontrol() {
    show("DRIVER");
    // Replace this loop with your joystick-driven routine.
    while (!pros::competition::is_disabled() && !pros::competition::is_autonomous()) pros::delay(20);
}
