/** RECF_Control_State deterministic protocol/state engine. MPL-2.0. */
#ifndef RECF_CONTROL_CORE_H
#define RECF_CONTROL_CORE_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#define RECF_DISABLED 1u
#define RECF_AUTONOMOUS 2u
#define RECF_CONNECTED 4u
#define RECF_LEASE_MS 1500u
#define RECF_FRAME_MAX 96u
#ifdef __cplusplus
extern "C" {
#endif
typedef enum { RECF_FIELD, RECF_STOP, RECF_AUTON, RECF_DRIVER } recf_mode_t;
typedef struct {
    bool enabled, selected, ready;
    recf_mode_t mode;
    uint32_t session, sequence, last_seen;
    uint8_t physical;
    const char *reason;
} recf_core_t;
typedef struct { char bytes[RECF_FRAME_MAX]; size_t length; bool dropping; uint32_t last_byte; } recf_parser_t;
typedef void (*recf_emit_fn)(const char *bytes, size_t size, void *user);
void recf_core_enable(recf_core_t *state, bool enabled);
uint8_t recf_core_status(recf_core_t *state, uint8_t physical, uint32_t now);
/** A complete line excluding newline. Returns an ASCII reply, including newline. */
size_t recf_core_command(recf_core_t *state, const char *line, uint8_t physical,
                         uint32_t now, char *reply, size_t capacity);
/** Reserved @RECF/1 frames are consumed; other input is forwarded unchanged. */
void recf_parser_feed(recf_parser_t *parser, uint8_t byte, uint32_t now,
                      recf_emit_fn ordinary, recf_emit_fn frame, void *user);
const char *recf_mode_name(recf_mode_t mode);
#ifdef __cplusplus
}
#endif
#endif
