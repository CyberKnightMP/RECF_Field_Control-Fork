/** RECF_Control_State kernel integration. MPL-2.0. */
#include "kapi.h"
#include "system/recf_control_state.h"
#include "system/recf_control_core.h"
#include "v5_api.h"
#include "pros/adi.h"
#include "vdml/registry.h"
#include <string.h>

static recf_core_t control;
static recf_parser_t parser;
static recf_watchdog_t watchdog;
static bool runtime_ready;
extern bool inp_buffer_post(uint8_t byte);
extern bool ser_output_write(const uint8_t *buffer, size_t size, bool noblock);
/** Downstream serial parsing (the original PROS serial daemon). */
extern void ser_process_byte(uint8_t byte);

void recf_control_enable(bool enabled) {
    rtos_suspend_all();
    recf_core_enable(&control, enabled);
    control.ready = runtime_ready;
    rtos_resume_all();
}
void recf_control_mark_ready(void) {
    rtos_suspend_all();
    runtime_ready = true; control.ready = true;
    rtos_resume_all();
}
bool recf_control_is_enabled(void) { return control.enabled; }
bool recf_control_is_selected(void) { return control.enabled && control.selected; }
uint8_t recf_control_get_physical_status(void) { return vexCompetitionStatus(); }
uint8_t recf_control_resolve(uint8_t physical) {
    uint32_t now = millis();
    rtos_suspend_all();
    uint8_t result = recf_core_status(&control, physical, now);
    result = recf_watchdog_status(&watchdog, result, now);
    rtos_resume_all();
    return result;
}
static void ordinary(const char *bytes, size_t len, void *ign) {
    (void)ign;
    for (size_t i = 0; i < len; ++i) ser_process_byte((uint8_t)bytes[i]);
}
static void frame(const char *bytes, size_t len, void *ign) {
    (void)len; (void)ign;
    char reply[128];
    uint8_t raw = vexCompetitionStatus();
    uint32_t now = millis();
    rtos_suspend_all();
    size_t n = strstr(bytes, " WATCH_")
        ? recf_watchdog_command(&watchdog, bytes, raw, now, runtime_ready, reply, sizeof(reply))
        : recf_core_command(&control, bytes, raw, now, reply, sizeof(reply));
    rtos_resume_all();
    // Raw, indivisible protocol records: independent of the user's COBS setting.
    if (n) ser_output_write((const uint8_t *)reply, n, true);
}
void recf_control_serial_byte(uint8_t byte) {
    recf_parser_feed(&parser, byte, millis(), ordinary, frame, NULL);
}
bool recf_control_output_blocked(void) {
    uint8_t raw = vexCompetitionStatus();
    uint8_t effective = recf_control_resolve(raw);
    return (watchdog.armed && watchdog.tripped) ||
        (recf_control_is_selected() && !(raw & RECF_CONNECTED) && (effective & RECF_DISABLED));
}
void recf_control_stop_motors(void) {
    port_mutex_take_all();
    rtos_suspend_all();
    for (uint8_t port = 0; port < INTERNAL_ADI_PORT; ++port) {
        v5_smart_device_s_t *device = registry_get_device_internal(port);
        if (device && device->device_type == E_DEVICE_MOTOR)
            vexDeviceMotorVoltageSet(device->device_info, 0);
        // Hold valve/analog/servo states. Only legacy PWM motors have an
        // unambiguous neutral command; include the Brain's internal ADI bank.
        if (device && device->device_info && (device->device_type == E_DEVICE_ADI || port == INTERNAL_ADI_PORT-1)) {
            for (uint8_t adi = 0; adi < 8; ++adi) {
                if ((int)vexDeviceAdiPortConfigGet(device->device_info, adi) == E_ADI_LEGACY_PWM)
                    vexDeviceAdiValueSet(device->device_info, adi, 0);
            }
        }
    }
    rtos_resume_all();
    port_mutex_give_all();
}
