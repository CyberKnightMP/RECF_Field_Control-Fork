/** RECF_Control_State kernel integration. MPL-2.0. */
#include "kapi.h"
#include "system/recf_control_state.h"
#include "system/recf_control_core.h"
#include "v5_api.h"
#include "vdml/registry.h"

static recf_core_t control;
static recf_parser_t parser;
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
    size_t n = recf_core_command(&control, bytes, raw, now, reply, sizeof(reply));
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
    return recf_control_is_selected() && !(raw & RECF_CONNECTED) && (effective & RECF_DISABLED);
}
void recf_control_stop_motors(void) {
    port_mutex_take_all();
    rtos_suspend_all();
    for (uint8_t port = 0; port < 21; ++port) {
        v5_smart_device_s_t *device = registry_get_device_internal(port);
        if (device && device->device_type == E_DEVICE_MOTOR)
            vexDeviceMotorVoltageSet(device->device_info, 0);
    }
    rtos_resume_all();
    port_mutex_give_all();
}
