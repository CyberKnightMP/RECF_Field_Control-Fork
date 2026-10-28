# Kernel identity — separate release v1.4.0

PROS's stock version marker identifies the upstream kernel version; it does not establish that a RECF patch is present. This release adds a compiled RECF compatibility descriptor to kernel@4.2.2-recf.4. The v1.4.0 app requires the exact descriptor before WATCH_ARM and refuses Enable on a missing or mismatched identity.

Fields: family `RECF_CONTROL_STATE`, upstream PROS `4.2.2`, RECF `1.4.0`, a 16-hex-digit source fingerprint and capability mask `0000000f` (native practice, heartbeat watchdog, ADI guard, identity).

## Desktop relay

Request over the existing Controller-to-Brain stdio FIFO transport:

```
@RECF/1 <sequence> <session> WATCH_ID
```

Response:

```
@RECF/1 <sequence> <session> ID RECF_CONTROL_STATE 4.2.2 1.4.0 <fingerprint> 0000000f
```

The session and sequence must match the app's current request. This read-only query does not renew the watchdog lease, consume its beat sequence, arm it or change modes. The app compares every descriptor field to its compiled expected value and displays the verified identity. A VEX transport ACK is insufficient. The full handshake is native Disabled → identity verification → WATCH_ARM → heartbeats → explicit phase Enable. There is no older-kernel fallback in v1.4.0; use the separate v1.3.0 app if compatibility with the earlier heartbeat kernel is needed.

## Robot program API

The same compiled descriptor is available locally:

```cpp
#include "main.h"
#include <cstdio>
void initialize() {
    std::printf("Kernel identity: %s\n", pros::c::recf_control_get_kernel_identity());
}
```

`kernel-identity.json` records the descriptor and individual hashes of the seven overlay sources and three integration/API headers. The source fingerprint is the first 16 hex digits of SHA-256 over the sorted compact JSON of those source hashes. Generated files are excluded to avoid a circular hash. `tools/kernel_identity.py --check` verifies that source files, compiled header and app expectation agree; kernel builds and CI reject stale identities. `tools/kernel_identity.py` regenerates it after an intentional firmware source change.

This is a version/build identification mechanism, not a digital signature or secure attestation. It has no private key, secure boot or hardware root of trust; modified software could imitate the descriptor. It identifies accidental stock/old/incompatible kernel installs. Artifact SHA-256 checksums verify download integrity separately.
