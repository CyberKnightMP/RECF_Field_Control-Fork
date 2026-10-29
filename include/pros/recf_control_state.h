/** RECF_Control_State: opt-in software competition control. MPL-2.0. */
#ifndef RECF_CONTROL_STATE_H
#define RECF_CONTROL_STATE_H
#include <stdbool.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
namespace pros { 
namespace c {
#endif
/**
 * \enum recf_status_e_t
 */
typedef enum recf_status_e {
    RECF_STATUS_DISABLED = 1u,
    RECF_STATUS_AUTONOMOUS = 2u,
    RECF_STATUS_CONNECTED = 4u
} recf_status_e_t;
/** 
 * Enable message control from initialize(). Default: false (stock PROS).
 * Physical competition control always has priority. Disabling this feature
 * returns to physical control; it does not mean a software STOP command.
 */
/** 
 * Read-only compiled kernel identity: family, PROS, RECF, build fingerprint and capabilities.
 * This is compatibility identification, not a cryptographic authenticity proof.
 * \return A string literal, e.g. "RECF/1 PROS/4.0.0-rc.3 kernel/2024-06-01+dev"
 */
const char *recf_control_get_kernel_identity(void);
/** 
 * Enable message control from initialize(). Default: false (stock PROS).
 * Physical competition control always has priority. Disabling this feature
 * returns to physical control; it does not mean a software STOP command.
 * \param enabled True to enable software control, false to disable.
 */
void recf_control_enable(bool enabled);
/** 
 * Mark the runtime as ready for software control. This is called automatically
 * after initialize() and after a competition mode transition. It is not necessary
 * to call this function after a software STOP command, but it is safe to do so.
 * \return boolean, True if the runtime is ready for software control, false otherwise.
 */
bool recf_control_is_enabled(void);
/** 
 * Get the physical VEX status, before software mode selection. 
 * \return A bitfield of RECF_DISABLED, RECF_AUTONOMOUS, and RECF_CONNECTED.
 */
uint8_t recf_control_get_physical_status(void);
/** 
 * True while software control is selected, including a timed-out STOP. 
 * \return boolean, True if software control is selected, false otherwise.
 */
bool recf_control_is_selected(void);
#ifdef __cplusplus
} 
}
}
#endif
#endif
