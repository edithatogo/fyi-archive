# Run log — 2026-08-30

Base cba7b0dec2734bdc9ff51c69610fc55cb1fc5aa1; isolated branch codex/foi-automation-recovery. Original donor checkout untouched. Receiver compatibility prerequisite reconciled in 0955f05 and independently validated before production commits.

Red: seven sync-summary regression tests failed before implementation. Two further regressions exposed noisy Python stdout and a destructive summary/state path collision, then passed after fixes. Recovery module import failed before its implementation; existing state regression rejects disjoint second leases. The controller dispatch regression failed with offset 0 despite an active lease, then passed. Integration tests exercise artifact retention, conflicting body replacement, rerun owner state and branch restrictions. A malformed conflict fixture was corrected to represent a valid concurrent controller update rather than malformed JSON.

Local validation: 901 tests passed and one skipped before the recovery workflow adapter was added; 93.38 percent suite coverage, pure recovery and summary modules each 100 percent line/branch coverage. Final expanded suite receipt follows. Ruff, CI preview formatting, ty and actionlint were run. Existing Make format disagreed with hosted CI; aligned it to the CI preview formatter instead of reformatting 45 unrelated files. make quality then reaches the unavailable local typos executable; this host-tool failure is not a code-quality pass.

Read-only prepare successfully observed issue365 and failed owner31929819944 through GitHub. No live state mutation, source capture, HF upload or takeover has been performed. Apply always obtains fresh observations; a saved local proposal must not be reused after its five-minute window.
