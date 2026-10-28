/** Kernel integration for RECF_Control_State. MPL-2.0. */
#pragma once
#include <stdint.h>
#include <stdbool.h>
uint8_t recf_control_resolve(uint8_t physical);
void recf_control_mark_ready(void);
/** Called only from the serial daemon; forwards ordinary bytes to stdin. */
void recf_control_serial_byte(uint8_t byte);
/** Zero smart-motor commands during software STOP and before mode transitions. */
void recf_control_stop_motors(void);

bool recf_control_output_blocked(void);
