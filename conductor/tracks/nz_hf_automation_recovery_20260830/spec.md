# Scope and authority

Implement AC02/AC03 of the approved receiver track global_foi_public_archive_20260830, phase P1. The user's implementation/public-archive request authorizes these active-owner repairs; it does not waive source rights/privacy or complete the takeover. Receiver parent issue: edithatogo/archive-govt-nz#233; phase issue #235; baseline PR #244.

Preserve completed coverage, original state receipts and existing dataset identities. Block overlapping/disjoint second leases and repeat dispatch while a lease exists. Release a failed exact owner only after retaining fresh diagnostic evidence, checking owner state twice, verifying the recovery artifact through GitHub, and rechecking the entire state. Share the current capture workflow concurrency group. Successful/live/unknown owners must not be released automatically.

The issue API has no claimed compare-and-swap here: all authorized writers must use the shared concurrency group. Out-of-band human/API writes during the final PATCH window remain a risk; never describe this as the cross-repository ownership fence required for later cutover.

Produce an atomic, typed sync summary artifact with diagnostics on stderr, reject path collisions and cross-instance/malformed card inputs, and retain bounded execution status on failure. Manifest verification must not imply full raw restoration. No new source, rights exception, public raw upload, scheduler takeover or donor retirement is included.
