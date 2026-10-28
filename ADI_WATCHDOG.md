# ADI and pneumatic behavior on watchdog STOP

Available in kernel@4.2.2-recf.3 (release v1.3.0) and later. The existing smart-motor watchdog remains in place.

When the watchdog is tripped, the kernel guards standard PROS ADI paths, including C/C++ digital outputs and Pneumatics, on both the internal Brain bank and external 3-wire expanders:

- Reject further digital/analog/servo output changes and port reconfiguration. Digital valves, analog outputs and legacy servos retain their last commanded state.
- Neutralize legacy PWM motors, including a command already active when the trip occurs, and keep neutralizing them while STOP is latched.
- Block addressable-LED transmission, which also toggles an ADI digital pin.
- Preserve ADI sensor reads. Guard configuration/value writes used inside sensor constructors as well so they cannot change a valve pin during STOP.

The check and low-level SDK write are protected against a task switch between them. Common public write APIs report EACCES/PROS_ERR for rejected commands; PWM motor commands become zero. Some sensor constructors retain their upstream return conventions even when an internal reconfiguration is suppressed, so initialize devices before running practice control.

The kernel deletes its managed autonomous/driver callback on the Disabled transition. Independently created tasks may keep running, but their standard PROS ADI and smart-motor writes are blocked. Arbitrarily killing all user tasks could deadlock locks held by those tasks, so this feature does not do that.

Holding a valve state prevents new software valve transitions. It does not vent pressure, cancel a cylinder stroke already underway, or guarantee a mechanically stationary actuator. Setting all valves low is not universally safe: it may retract or extend cylinders depending on plumbing and reversal. This release therefore does not force a global valve value. Direct VEX SDK calls and other unpatched hardware paths remain outside coverage.

Native tests exercise the actual production setter bodies and stop routine against simulated internal and expander devices, including PWM neutralization, valve/servo hold, LED rejection and normal behavior after re-arming. Hardware validation is pending.
