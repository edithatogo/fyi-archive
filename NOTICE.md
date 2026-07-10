# NOTICE

## Project

**fyi-archive** — a read-only, full-site archive of [fyi.org.nz](https://fyi.org.nz/)
and the separate `au-rtk` collection from
[righttoknow.org.au](https://www.righttoknow.org.au/), both running on the
[Alaveteli](https://alaveteli.org/) platform.

## Provenance

All archived data originates from public, read-only endpoints of the configured source
instance. The NZ collection uses `fyi.org.nz`; the AU collection uses
`righttoknow.org.au` and is kept separate in manifests, storage, and publication.
No account, login, or write/submit operations are used. Capture is performed by the
companion tool [`fyi-cli`](https://github.com/edithatogo/fyi-cli) using only documented,
publicly available endpoints.

## Not an official source

- This repository is **not affiliated with, endorsed by, or representative of** the
  operators of fyi.org.nz, righttoknow.org.au, the Alaveteli project, or any public
  body.
- The archived material reflects the public site at a point in time and is **not** a
  substitute for the live, authoritative record at `fyi.org.nz`.
- fyi.org.nz content is © its respective contributors under the terms displayed on the
  live site; this archive preserves that content for research, transparency, and
  reproducibility purposes only.

## Copyright & licensing (summary)

Archived content is already-published, public material from the configured source. The archive
asserts **no new rights** over it and records each item's source-declared licence
(e.g. CC BY 4.0 under NZGOAL, "no known rights", or private-author text) in the
manifest. The **code** in this repo is MIT; the **data** retains the source's rights
status. NZ material is governed by the Copyright Act 1994 and NZGOAL; Australian
material is governed in part by the Copyright Act 1968 (Cth) and its source terms.
Full provisions, citations, and the instance-aware takedown process are in
[`docs/copyright-and-licensing.md`](docs/copyright-and-licensing.md).

## Politeness

Harvesting is deliberately rate-limited, `robots.txt`-aware, and run with a
descriptive, contactable `User-Agent`. See
[`docs/ethics-and-compliance.md`](docs/ethics-and-compliance.md).

## Contact

Maintainer: Dylan Mordaunt — `edithatogo@users.noreply.github.com`
