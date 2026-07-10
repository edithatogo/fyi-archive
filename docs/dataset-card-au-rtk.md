---
pretty_name: "fyi-archive-au-rtk"
license: mit
language:
  - en
tags:
  - australia
  - freedom-of-information
  - alaveteli
  - web-archive
  - warc
  - wacz
  - government-transparency
---

# fyi-archive-au-rtk

Dataset-card draft for a faithful, read-only archive of
**[righttoknow.org.au](https://www.righttoknow.org.au/)**, Australia's public
freedom-of-information request register running on [Alaveteli](https://alaveteli.org/).

The archive is for public-interest and policy research, journalism, and reproducible
historical preservation. It is **not** collected or published for AI training,
fine-tuning, evaluation, or generative-AI input. The AU instance is kept separate from
the NZ `fyi-archive-nz` collection.

## Source provenance

- **Upstream:** `https://www.righttoknow.org.au/` (public read-only endpoints only;
  no login or write/submit operations).
- **Capture tool:** [`fyi-cli`](https://github.com/edithatogo/fyi-cli), with
  rate-limited enumeration and faithful WARC/WACZ capture.
- **Orchestration:** [`fyi-archive`](https://github.com/edithatogo/fyi-archive),
  using the `au-rtk` instance configuration.

## Rights and licensing

Public availability does not by itself grant a blanket reuse licence. The archive
preserves source-declared licences, attribution, and rights notices and records them
in the manifest where available. Australian copyright questions are governed in part
by the [Copyright Act 1968 (Cth)](https://www.legislation.gov.au/C1968A00063/latest/text);
the archive makes no determination that an individual request, response, or
attachment is reusable. The repository code is MIT; archived data retains the rights
status of its source. See
[`docs/copyright-and-licensing.md`](copyright-and-licensing.md).

## Operational safeguards

Capture is read-only, `robots.txt`-aware, rate-limited, and bounded by independent
per-instance state. Where the source publishes Content-Signal directives, the
archive records and honors them. The archive's own policy is `ai-train=no` and
`ai-input=no`; Content Signals are publisher preferences and do not replace legal
permission. See [`docs/ethics-and-compliance.md`](ethics-and-compliance.md).

## Takedown

Rights-holder requests should include `au-rtk`, the source URL, request id, and the
reason for the request. Contact `edithatogo@users.noreply.github.com`.
