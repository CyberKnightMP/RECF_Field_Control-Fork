/** RECF_Control_State deterministic protocol/state engine. MPL-2.0. */
#include "system/recf_control_core.h"
#include "system/recf_kernel_identity.h"
#include <stdio.h>
#include <string.h>
#include <limits.h>

const char *recf_control_get_kernel_identity(void) { return RECF_KERNEL_DESCRIPTOR; }

const char *recf_mode_name(recf_mode_t mode) {
    static const char *const names[] = {"FIELD", "STOP", "AUTON", "DRIVER"};
    return names[mode];
}
void recf_core_enable(recf_core_t *s, bool enabled) {
    memset(s, 0, sizeof(*s));
    s->enabled = enabled;
    s->ready = true;
    s->reason = enabled ? "READY" : "LOCKED";
}
uint8_t recf_core_status(recf_core_t *s, uint8_t raw, uint32_t now) {
    s->physical = raw;
    if (raw & RECF_CONNECTED) {
        if (s->selected) {
            s->session = 0;
            s->mode = RECF_STOP;
            s->reason = "FIELD";
        }
        return raw;
    }
    if (!s->enabled || !s->selected) return raw;
    if (s->session && (uint32_t)(now - s->last_seen) >= RECF_LEASE_MS) {
        s->session = 0;
        s->mode = RECF_STOP;
        s->reason = "TIMEOUT";
    }
    // A physical disabled state cannot be cleared by software.
    if (raw & RECF_DISABLED) return raw;
    uint8_t bits = s->mode == RECF_AUTON ? RECF_AUTONOMOUS :
                   s->mode == RECF_STOP ? RECF_DISABLED : 0;
    return (raw & (uint8_t)~(RECF_DISABLED | RECF_AUTONOMOUS)) | bits;
}
static bool number(const char **p, uint32_t *out) {
    uint32_t n = 0;
    if (**p < '0' || **p > '9') return false;
    while (**p >= '0' && **p <= '9') {
        uint32_t d = (uint32_t)(*(*p)++ - '0');
        if (n > (UINT32_MAX - d) / 10u) return false;
        n = n * 10u + d;
    }
    if (**p != ' ') return false;
    ++*p; *out = n; return n != 0;
}
size_t recf_core_command(recf_core_t *s, const char *line, uint8_t raw,
                         uint32_t now, char *reply, size_t cap) {
    uint32_t seq = 0, token = 0;
    const char *p = line, *error = NULL;
    uint8_t effective = recf_core_status(s, raw, now);
    if (strncmp(p, "@RECF/1 ", 8) || (p += 8, !number(&p, &seq)) || !number(&p, &token)) {
        error = "FORMAT";
    } else if (!strcmp(p, "STATUS")) {
        // Read-only probes never claim control or refresh the lease.
    } else if (!s->enabled) error = "LOCKED";
    else if (!s->ready) error = "STARTING";
    else if (raw & (RECF_CONNECTED | RECF_DISABLED)) error = "FIELD";
    else if (!strcmp(p, "HELLO")) {
        if (s->session && s->session != token) error = "BUSY";
        else if (s->session == token) error = "SESSION_EXISTS";
        else {
            s->session = token; s->sequence = seq; s->last_seen = now;
            s->selected = true; s->mode = RECF_STOP; s->reason = "CLAIMED";
        }
    } else if (!s->session || s->session != token) error = "SESSION";
    else if (seq <= s->sequence) error = "STALE";
    else if (!strcmp(p, "STOP") || !strcmp(p, "AUTON") || !strcmp(p, "DRIVER") ||
             !strcmp(p, "PING") || !strcmp(p, "RELEASE")) {
        s->sequence = seq; s->last_seen = now;
        if (!strcmp(p, "RELEASE")) {
            s->selected = false; s->session = 0; s->mode = RECF_FIELD; s->reason = "RELEASED";
        } else if (strcmp(p, "PING")) {
            s->mode = !strcmp(p, "AUTON") ? RECF_AUTON : !strcmp(p, "DRIVER") ? RECF_DRIVER : RECF_STOP;
            s->reason = "COMMAND";
        }
    } else error = "COMMAND";
    effective = recf_core_status(s, raw, now);
    const char *mode = effective & RECF_DISABLED ? "STOP" :
                       effective & RECF_AUTONOMOUS ? "AUTON" : "DRIVER";
    const char *source = raw & RECF_CONNECTED ? "FIELD" : s->selected && s->enabled ? "SOFTWARE" : "PHYSICAL";
    int n = snprintf(reply, cap, "@RECF/1 %lu %lu %s %s %s %u %s\n",
                     (unsigned long)seq, (unsigned long)token, error ? "ERR" : "OK", mode, source,
                     (unsigned)raw, error ? error : s->reason ? s->reason : "READY");
    return n > 0 && (size_t)n < cap ? (size_t)n : 0;
}
void recf_parser_feed(recf_parser_t *p, uint8_t b, uint32_t now,
                      recf_emit_fn ordinary, recf_emit_fn frame, void *user) {
    const char prefix[] = "@RECF/1 ";
    if ((p->length || p->dropping) && (uint32_t)(now - p->last_byte) >= 500u) {
        // Incomplete reserved frames expire; a partial nonreserved prefix is returned.
        if (p->length < sizeof(prefix) - 1 && p->length) ordinary(p->bytes, p->length, user);
        p->length = 0; p->dropping = false;
    }
    p->last_byte = now;
    if (p->dropping) { if (b == '\n') p->dropping = false; return; }
    if (!p->length && b != '@') { char c = (char)b; ordinary(&c, 1, user); return; }
    if (p->length < sizeof(prefix) - 1 && b != (uint8_t)prefix[p->length]) {
        ordinary(p->bytes, p->length, user); p->length = 0;
        if (b == '@') p->bytes[p->length++] = (char)b;
        else { char c = (char)b; ordinary(&c, 1, user); }
        return;
    }
    if (b == '\n') {
        p->bytes[p->length] = 0;
        frame(p->bytes, p->length, user); p->length = 0; return;
    }
    if (p->length >= RECF_FRAME_MAX - 1 || b < 32 || b > 126) {
        p->length = 0; p->dropping = true; return;
    }
    p->bytes[p->length++] = (char)b;
}

/* Independent of software mode selection: guards native practice field modes. */
uint8_t recf_watchdog_status(recf_watchdog_t *w, uint8_t status, uint32_t now) {
    if (!w->armed) return status;
    if (!w->tripped && (uint32_t)(now - w->last_seen) >= RECF_WATCHDOG_MS) {
        w->tripped = true;
        w->reason = "TIMEOUT";
    }
    return w->tripped ? (uint8_t)(status | RECF_DISABLED) : status;
}
size_t recf_watchdog_command(recf_watchdog_t *w, const char *line,
                            uint8_t raw, uint32_t now, bool ready,
                            char *reply, size_t cap) {
    uint32_t seq = 0, token = 0;
    const char *p = line, *error = NULL;
    recf_watchdog_status(w, raw, now);
    if (strncmp(p, "@RECF/1 ", 8) || (p += 8, !number(&p, &seq)) || !number(&p, &token)) error = "FORMAT";
    else if (!strcmp(p, "WATCH_ID")) {
        int n = snprintf(reply, cap, "@RECF/1 %lu %lu ID %s\n",
            (unsigned long)seq, (unsigned long)token, recf_control_get_kernel_identity());
        return n > 0 && (size_t)n < cap ? (size_t)n : 0;
    }
    else if (!strcmp(p, "WATCH_STATUS")) { /* Never renews the lease. */ }
    else if (!ready) error = "STARTING";
    else if (!strcmp(p, "WATCH_ARM")) {
        if (!(raw & RECF_DISABLED)) error = "NOT_DISABLED";
        else if (w->session == token) error = "SESSION_EXISTS";
        else if (w->armed && !w->tripped) error = "BUSY";
        else {
            w->armed = true; w->tripped = false;
            w->session = token; w->sequence = seq; w->last_seen = now;
            w->reason = "ARMED";
        }
    } else if (!w->armed || w->session != token) error = "SESSION";
    else if (seq <= w->sequence) error = "STALE";
    else if (!strcmp(p, "WATCH_STOP")) {
        w->sequence = seq; w->tripped = true; w->reason = "STOPPED";
    } else if (!strcmp(p, "WATCH_BEAT")) {
        if (w->tripped) error = "EXPIRED";
        else { w->sequence = seq; w->last_seen = now; w->reason = "HEARTBEAT"; }
    } else error = "COMMAND";
    uint8_t effective = recf_watchdog_status(w, raw, now);
    const char *mode = effective & RECF_DISABLED ? "STOP" : effective & RECF_AUTONOMOUS ? "AUTON" : "DRIVER";
    int n = snprintf(reply, cap, "@RECF/1 %lu %lu %s %s WATCHDOG %u %s\n",
        (unsigned long)seq, (unsigned long)token, error ? "ERR" : "OK", mode,
        (unsigned)raw, error ? error : w->reason ? w->reason : "UNARMED");
    return n > 0 && (size_t)n < cap ? (size_t)n : 0;
}
