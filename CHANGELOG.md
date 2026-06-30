# Changelog

All notable changes to this project are documented here.

This file is managed by `release-please` from Conventional Commits after the initial
bootstrap release.

## [0.4.0](https://github.com/edithatogo/fyi-archive/compare/fyi_archive-v0.3.0...fyi_archive-v0.4.0) (2026-06-30)


### Features

* auto-merge backfill worker artifacts ([5d3269f](https://github.com/edithatogo/fyi-archive/commit/5d3269fd85040c1358f5c4f72d8ec7beea874949))

## [0.3.0](https://github.com/edithatogo/fyi-archive/compare/fyi_archive-v0.2.1...fyi_archive-v0.3.0) (2026-06-30)


### Features

* automate historical backfill dispatch ([5ff90dd](https://github.com/edithatogo/fyi-archive/commit/5ff90dd82cd032aef26b6c11ebbeb607bfe50c49))


### Bug Fixes

* isolate automated backfill smoke state ([dc4ce1d](https://github.com/edithatogo/fyi-archive/commit/dc4ce1da16d0a81badeb7509e80c8ba02bacbe34))
* persist new backfill state issue ([8d825d9](https://github.com/edithatogo/fyi-archive/commit/8d825d98d6fcd7c5c8615b3aa196ed25e34cd9ab))

## [0.2.1](https://github.com/edithatogo/fyi-archive/compare/fyi_archive-v0.2.0...fyi_archive-v0.2.1) (2026-06-29)


### Bug Fixes

* complete release version propagation ([cfbecd6](https://github.com/edithatogo/fyi-archive/commit/cfbecd67060de5bb9d3b6adfe625dd070f34365c))

## [0.2.0](https://github.com/edithatogo/fyi-archive/compare/fyi_archive-v0.1.0...fyi_archive-v0.2.0) (2026-06-29)


### Features

* add chunked historical backfill workflow ([b3e6301](https://github.com/edithatogo/fyi-archive/commit/b3e6301e1b6a182ef1cb8ea4bbbeaa1b597a8ae9))
* add CI/CD foundation workflows ([a5f5ea8](https://github.com/edithatogo/fyi-archive/commit/a5f5ea8d17d4e0cb88c4b8c83167b9ae77c5a4f5))
* add CI/CD foundation workflows ([72fe506](https://github.com/edithatogo/fyi-archive/commit/72fe506d1605d841ae762261b78f9f7c74ddf088))
* add release workflow ([3a06b04](https://github.com/edithatogo/fyi-archive/commit/3a06b04ad01f1a0282361f7536c5f4652c828ff1))
* add security supply chain tooling ([707f9f6](https://github.com/edithatogo/fyi-archive/commit/707f9f64a13c08ad015242d37bac84a73092941a))
* add versioned mirror verification ([69229a4](https://github.com/edithatogo/fyi-archive/commit/69229a42157d711b67e429a60a21feac21e5b878))
* initial scaffold ([f99f9df](https://github.com/edithatogo/fyi-archive/commit/f99f9df6f12027e4565d148a064d07bfe82370bb))
* merge backfill chunk manifests ([ee23cd4](https://github.com/edithatogo/fyi-archive/commit/ee23cd47e46bb3e6480c085d62c763849fdbebdb))
* **observability:** enforce archive parity checks ([ff18791](https://github.com/edithatogo/fyi-archive/commit/ff1879108d8520a8d7fe9b9b67900db230a4cb52))
* **publish:** add multi-mirror publish adapters ([3b47922](https://github.com/edithatogo/fyi-archive/commit/3b47922074bb2ed75a7d5cd8bac2379e12f52d92))
* **publish:** build capped seed bundle before publish ([0cffe0f](https://github.com/edithatogo/fyi-archive/commit/0cffe0f6ded6c9cb8789dfd2a8b86f0b8f25c089))
* **publish:** schedule monthly archive refresh ([0f8e9be](https://github.com/edithatogo/fyi-archive/commit/0f8e9be67e19ad3a463a8bf0582206a3f7c4a5d1))
* **publish:** verify mirror artifact evidence ([30281f9](https://github.com/edithatogo/fyi-archive/commit/30281f9c3f5cdb9b8e79334a6112dd068de1fc1f))
* **release:** configure release version propagation ([176bca6](https://github.com/edithatogo/fyi-archive/commit/176bca6aee5c771d73651dd320cb57268073c35d))
* **security:** add release provenance evidence ([26f8e34](https://github.com/edithatogo/fyi-archive/commit/26f8e344fa1fc2459dc412a93ce62681981956c2))
* **seed:** add historical seed orchestration ([ed9a362](https://github.com/edithatogo/fyi-archive/commit/ed9a3627e30ab0e75cf4beffe57caa1ec3aece03))
* **seed:** prove live smoke archive path ([2ff70d7](https://github.com/edithatogo/fyi-archive/commit/2ff70d77fb2541b9b0e7a4fb63b9df0ab9bf2fd3))
* **sync:** add prospective hf sync scaffold ([9cb9342](https://github.com/edithatogo/fyi-archive/commit/9cb9342f72134be3e9838f20594aa61b87c90cc8))


### Bug Fixes

* build live historical seed manifests ([3a991b4](https://github.com/edithatogo/fyi-archive/commit/3a991b42828ce4328a61770a317a44df86362732))
* **ci:** lock fyi-cli from github ([efbb26d](https://github.com/edithatogo/fyi-archive/commit/efbb26d36c1308376950dedb3e6de91ce1e81826))
* **ci:** remove unreachable uv path source ([ce3260d](https://github.com/edithatogo/fyi-archive/commit/ce3260dd87ea31264586e61124dcaf0f8e11a8f9))
* **ci:** repair docs and release workflows ([9e3cef5](https://github.com/edithatogo/fyi-archive/commit/9e3cef53c1b5e853ed6376e213781561a2cb89d1))
* discover live historical seed requests ([b5f2181](https://github.com/edithatogo/fyi-archive/commit/b5f21818b11d7e7a9c8e8924c538593c514bd324))
* fall back when FYI discovery times out ([3072887](https://github.com/edithatogo/fyi-archive/commit/3072887286512647822c3f852c98951e070d16af))
* make publish evidence self-contained ([1574304](https://github.com/edithatogo/fyi-archive/commit/1574304c050c67720f11515e67c432221494610a))
* preserve backfill failure evidence ([40c8b98](https://github.com/edithatogo/fyi-archive/commit/40c8b988a210f54b7c27c40c681ab530b0c1a595))
* preserve chunk ids in dry-run backfills ([d12fd93](https://github.com/edithatogo/fyi-archive/commit/d12fd93b177cc48e5311a07199c0bf3f36fd19a3))
* preserve publish seed failure evidence ([b69a35c](https://github.com/edithatogo/fyi-archive/commit/b69a35c7f320027ce9d736b59fb57b02e8e3542c))
* publish metadata to archival mirrors ([99f099d](https://github.com/edithatogo/fyi-archive/commit/99f099db8e04cc8f3c2ec59d8e879140ede30ff8))
* **publish:** build live seed manifest from capture output ([1a0b698](https://github.com/edithatogo/fyi-archive/commit/1a0b698f35cb67a93a87c2f7f85a67ca8b79fb21))
* **publish:** clean hf dataset mirror before upload ([700af67](https://github.com/edithatogo/fyi-archive/commit/700af6777fff66d3507698aa832113857e68cfc8))
* **publish:** commit hf dataset artifacts atomically ([f82b616](https://github.com/edithatogo/fyi-archive/commit/f82b61674e8ed3128782c4bd80e2bf61133ba317))
* **publish:** pass provenance globs literally ([22f10d6](https://github.com/edithatogo/fyi-archive/commit/22f10d65f74cf701aac8fc50935c88f2aa71ca56))
* **publish:** preserve hf commit across skipped files ([345ba32](https://github.com/edithatogo/fyi-archive/commit/345ba32e2056aa72b2098efff606980538565cb9))
* **publish:** stage hf artifacts outside dist ([051f7ee](https://github.com/edithatogo/fyi-archive/commit/051f7ee5e1d889a531837db647a4db8b001d6cc5))
* **publish:** upload ignored hf artifacts explicitly ([18d6fdd](https://github.com/edithatogo/fyi-archive/commit/18d6fdd60cd59267f9a4c1a6d4ed6f030c14e6ae))
* **publish:** upload staged hf dataset artifacts ([0d5cadc](https://github.com/edithatogo/fyi-archive/commit/0d5cadcf7634a98bc9e6500e6dd4b24e08ab7a9e))
* **publish:** verify hf manifest at uploaded commit ([1da85a7](https://github.com/edithatogo/fyi-archive/commit/1da85a73e5550139b40599743a7064ca19b00a18))
* **publish:** verify hf manifest from fresh snapshot ([a1579ff](https://github.com/edithatogo/fyi-archive/commit/a1579fff9cf85ac86e30476dd672a142f6641911))
* resolve publish verification roots ([a94c47e](https://github.com/edithatogo/fyi-archive/commit/a94c47e45bfe86e616465973ffb7d041273bea32))
* retry live FYI discovery ([998d8b5](https://github.com/edithatogo/fyi-archive/commit/998d8b59d153b869a5e63793d1f49fca35e19326))
* retry transient Hugging Face commits ([783f986](https://github.com/edithatogo/fyi-archive/commit/783f986c3baa5821f18cf84cfdce5fb36b56d237))
* **sync:** compare restored requests with raw diff hashes ([d575583](https://github.com/edithatogo/fyi-archive/commit/d5755832fb946748668f4a2722d1a8350e8c9016))
* **sync:** publish changed manifests before verification ([d29480b](https://github.com/edithatogo/fyi-archive/commit/d29480b80e6cba610049dde72fc3e973a85db73e))
* **sync:** restore hf dataset before prospective diff ([b7aa88b](https://github.com/edithatogo/fyi-archive/commit/b7aa88b56a0ce4484595509f2931a4125ece8db0))
* tolerate existing HF repo rate limits ([a0f9300](https://github.com/edithatogo/fyi-archive/commit/a0f930080ca8a80e55ad886e38b0b6db6f0d2dab))


### Documentation

* align repo structure notes ([9e59e8c](https://github.com/edithatogo/fyi-archive/commit/9e59e8c09504292129e40cc6a83bb2d62f03d162))
* **conductor:** update archive blocker status ([1b61401](https://github.com/edithatogo/fyi-archive/commit/1b614014a02e2f187c91048aaf1d73948677a2a0))
* mark CI/CD foundation track complete ([365aa0d](https://github.com/edithatogo/fyi-archive/commit/365aa0d774edc8ec2a57e98353cc5294a4f73e81))
* mark repo_bootstrap complete ([7ba759d](https://github.com/edithatogo/fyi-archive/commit/7ba759de1e72f71e1ea3ee26cc7425d8029288e8))

## [0.1.0] - 2026-06-27

### Added

- Initial repository scaffold, Conductor context, CI/quality tooling, and release
  automation skeleton.
