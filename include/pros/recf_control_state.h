/** RECF_Control_State: opt-in software competition control. MPL-2.0. */
#ifndef RECF_CONTROL_STATE_H
#define RECF_CONTROL_STATE_H
#include <stdbool.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
namespace pros { namespace c {
#endif
/** Enable message control from initialize(). Default: false (stock PROS).
 * Physical competition control always has priority. Disabling this feature
 * returns to physical control; it does not mean a software STOP command.
 */
/** Read-only compiled kernel identity: family, PROS, RECF, build fingerprint and capabilities.
 * This is compatibility identification, not a cryptographic authenticity proof.
 */
const char *recf_control_get_kernel_identity(void);
void recf_control_enable(bool enabled);
bool recf_control_is_enabled(void);
/** Physical VEX status, before software mode selection. */
uint8_t recf_control_get_physical_status(void);
/** True while software control is selected, including a timed-out STOP. */
bool recf_control_is_selected(void);
#ifdef __cplusplus
} }
}
#endif
#endif
