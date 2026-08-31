# Run log — 2026-08-30

Base cba7b0dec2734bdc9ff51c69610fc55cb1fc5aa1; isolated branch codex/foi-automation-recovery. Original donor checkout untouched. Receiver compatibility prerequisite reconciled in 0955f05 and independently validated before production commits.

Red: seven sync-summary regression tests failed before implementation. Two further regressions exposed noisy Python stdout and a destructive summary/state path collision, then passed after fixes. Recovery module import failed before its implementation; existing state regression rejects disjoint second leases. The controller dispatch regression failed with offset 0 despite an active lease, then passed. Integration tests exercise artifact retention, conflicting body replacement, rerun owner state and branch restrictions. A malformed conflict fixture was corrected to represent a valid concurrent controller update rather than malformed JSON.

Local validation: 901 tests passed and one skipped before the recovery workflow adapter was added; 93.38 percent suite coverage, pure recovery and summary modules each 100 percent line/branch coverage. Final expanded suite receipt follows. Ruff, CI preview formatting, ty and actionlint were run. Existing Make format disagreed with hosted CI; aligned it to the CI preview formatter instead of reformatting 45 unrelated files. make quality then reaches the unavailable local typos executable; this host-tool failure is not a code-quality pass.

Read-only prepare successfully observed issue365 and failed owner31929819944 through GitHub. No live state mutation, source capture, HF upload or takeover has been performed. Apply always obtains fresh observations; a saved local proposal must not be reused after its five-minute window.

Final expanded core suite: make test-all passed 907 tests, one skipped, 93.38 percent coverage. CI-equivalent Ruff/preview formatting/ty, changed-workflow actionlint, and typos1.47.2 passed. The typos binary was staged outside the repo from its CI-pinned GitHub release after SHA-256 verification. make quality now stops at missing local Taplo; no TOML changed and the hosted workflow installs it separately. This limitation is recorded, not suppressed. Final card wording explicitly limits verification to the manifest; targeted renderer/recovery checks passed afterward. validation.json contains output digests and the live read-only preparation receipt.

Hosted advisory preview lint caught three missing explicit UTF-8 encodings in newly added receipt/test paths. Fixed in a0a4d45; whole-repo preview lint and ty pass, and six integration tests pass. Hosted required repository-quality (including Taplo) passed on the initial implementation head; fresh checks remain required on the corrected head.

## Attachment gaps and failure-reporting recovery — 2026-08-31

Two red tests showed absent attachment census; implemented census retention and rejection of queue credit after cold restoration when expected attachment references have no retained response. Focused raw and shell-injection regressions: 17 passed. Full suite: 923 passed, one skipped, 93.42% coverage (before adding the independently passing shell regression).

Required make quality first found preview-format drift; corrected. The next attempt identified missing Taplo; downloaded upstream 0.10.0 into temporary tools. Complete local workflow lint then exposed baseline unused-variable/redirection warnings and actual backtick command substitution in CI failure reporting. Recorded and corrected these specific findings; quoted environment values preserve workflow names as data. The first unused-variable edit also touched an active loop; inspection caught it immediately and restored that loop before final validation. Final make quality passed including actionlint with shellcheck enabled. Taplo warns about an absent optional config and uses defaults. No monitor resume or publication occurred.

PR 408 hosted substantive checks passed; preview lint found one missing explicit UTF-8 encoding in the new workflow regression. Added UTF-8 to the test and the newly introduced metadata reads for cross-platform consistency. Running preview lint, quality and the full suite again before updating the head.

Encoding correction validated: `uv run ruff check --preview .` and full `make quality` passed. Full test suite passed 924 tests with one skip, 93.42% coverage. Hosted checks will be re-observed at the updated exact head; no workflow has been enabled.
