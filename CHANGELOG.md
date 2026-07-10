# Changelog

All notable changes to this project are documented here.

This file is managed by `release-please` from Conventional Commits after the initial
bootstrap release.

## [0.7.0](https://github.com/edithatogo/fyi-archive/compare/fyi_archive-v0.6.0...fyi_archive-v0.7.0) (2026-07-10)


### Features

* add AU jurisdiction taxonomy ([#100](https://github.com/edithatogo/fyi-archive/issues/100)) ([87f3d7c](https://github.com/edithatogo/fyi-archive/commit/87f3d7c0437738c7dc00a4fb9bf9c551c1730c08))
* consume fyi-cli body discovery ([f54f8b0](https://github.com/edithatogo/fyi-archive/commit/f54f8b054a32edc3a7a38869536645e0d204d6e3))


### Documentation

* add AU RTK ethics and rights policy ([#98](https://github.com/edithatogo/fyi-archive/issues/98)) ([e8134f2](https://github.com/edithatogo/fyi-archive/commit/e8134f298309e3c7653374a648614c7c8598d415))
* complete AU taxonomy track ([e20ad31](https://github.com/edithatogo/fyi-archive/commit/e20ad318cf4d40aedd1baf2a9f42629564f9cfad))

## [0.6.0](https://github.com/edithatogo/fyi-archive/compare/fyi_archive-v0.5.5...fyi_archive-v0.6.0) (2026-07-09)


### Features

* wire --instance through backfill and seed workflows ([2f6d1b4](https://github.com/edithatogo/fyi-archive/commit/2f6d1b4efa832158776c4cc45322fb1c92fddb9c))
* wire rate limiting flags and add seed_cap to instance registry ([8647bf9](https://github.com/edithatogo/fyi-archive/commit/8647bf9a5ee78201e55bf91585c5b2e6e345e3cf))


### Bug Fixes

* propagate seed_cap through resolve_instance base_url override ([3da4fa6](https://github.com/edithatogo/fyi-archive/commit/3da4fa6b1be2e1812fe4c4bbb89b763ea48a9782))


### Documentation

* add clear messaging about rate limits and AI use ([a9aa01e](https://github.com/edithatogo/fyi-archive/commit/a9aa01ed73ba34754207234a4faa8d188cf85bd4))

## [0.5.5](https://github.com/edithatogo/fyi-archive/compare/fyi_archive-v0.5.4...fyi_archive-v0.5.5) (2026-07-09)


### Bug Fixes

* skip redundant GraphQL mutations for already-tagged items ([18005e7](https://github.com/edithatogo/fyi-archive/commit/18005e7468f9dbabb4841c49c104ea245211dab8))

## [0.5.4](https://github.com/edithatogo/fyi-archive/compare/fyi_archive-v0.5.3...fyi_archive-v0.5.4) (2026-07-09)


### Documentation

* update Zenodo DOI citation ([#51](https://github.com/edithatogo/fyi-archive/issues/51)) ([dfb40a8](https://github.com/edithatogo/fyi-archive/commit/dfb40a870fd0a077bad1cba93d17197a16f44174))

## [0.5.3](https://github.com/edithatogo/fyi-archive/compare/fyi_archive-v0.5.2...fyi_archive-v0.5.3) (2026-07-09)


### Bug Fixes

* adopt shared org code-scanning gate (issue [#27](https://github.com/edithatogo/fyi-archive/issues/27)) ([#44](https://github.com/edithatogo/fyi-archive/issues/44)) ([1c5375f](https://github.com/edithatogo/fyi-archive/commit/1c5375f19f4441521ee479cd4eaaf5525cc76c08))
* allow empty backfill merge manifests ([9b3c7ad](https://github.com/edithatogo/fyi-archive/commit/9b3c7ada3740d32347ce0adff6a3af6e9ff80d2f))
* clear backfill verification lint ([78138f9](https://github.com/edithatogo/fyi-archive/commit/78138f97ad09f003ed794a39386756e60ff2e793))
* compress backfill issue state ([3c99961](https://github.com/edithatogo/fyi-archive/commit/3c999616bcd13b8cf286a96c67a9d03ee0fa2499))
* compress backfill issue state ([4d949e0](https://github.com/edithatogo/fyi-archive/commit/4d949e02660cc2fcc2edd6975cef9ca7f3bc810e))
* refresh backfill state summary counts ([ff64aca](https://github.com/edithatogo/fyi-archive/commit/ff64aca2a8dd4be72f195ca05df2ffcdedbc2b52))
* satisfy backfill verification type checks ([726d3b0](https://github.com/edithatogo/fyi-archive/commit/726d3b0faf8c431c524f1ed94cf5ff8d1be6d52f))


### Documentation

* reconcile conductor state and add backfill ops runbook ([#34](https://github.com/edithatogo/fyi-archive/issues/34)) ([d2435a2](https://github.com/edithatogo/fyi-archive/commit/d2435a2e629fc3ecd84b3d1558da83de5fc53f23))

## [0.5.2](https://github.com/edithatogo/fyi-archive/compare/fyi_archive-v0.5.1...fyi_archive-v0.5.2) (2026-07-06)


### Bug Fixes

* redact security inventory outputs ([527e433](https://github.com/edithatogo/fyi-archive/commit/527e433288a9cd2cd950b8cf05c1bfabbea03a5a))
* redact security inventory outputs ([7d5ed50](https://github.com/edithatogo/fyi-archive/commit/7d5ed508394ef8eba357d38712c3d572aab1ed5b))


### Documentation

* add code owners for sensitive paths ([ba14fae](https://github.com/edithatogo/fyi-archive/commit/ba14fae6d6f6be2e6c406afd9de7a12c96a3b38b))
* add code owners for sensitive paths ([9dbc3af](https://github.com/edithatogo/fyi-archive/commit/9dbc3afad2c5ca7ddb8aa19bced2b780e26cd943))
* protect code owners file ([a71da4a](https://github.com/edithatogo/fyi-archive/commit/a71da4a81360d5691f2fb6de57c4816cc3e9a9f7))

## [0.5.1](https://github.com/edithatogo/fyi-archive/compare/fyi_archive-v0.5.0...fyi_archive-v0.5.1) (2026-07-03)


### Bug Fixes

* clear backfill verification lint ([b0404ee](https://github.com/edithatogo/fyi-archive/commit/b0404ee23f8378bd5d224763ddc6e7cbc5956b71))
* dispatch backfill batches without delay ([8eaa844](https://github.com/edithatogo/fyi-archive/commit/8eaa844b66a4f669919b76d17d7f6d5863751b95))
* dispatch backfill batches without delay ([2cc9d6b](https://github.com/edithatogo/fyi-archive/commit/2cc9d6b34865cc0ecb79715fa27bb505b23453ba))
* keep backfill worker pool topped up ([1b79aed](https://github.com/edithatogo/fyi-archive/commit/1b79aed632713a2c3a944ddbaebe7a1b13f46c4b))
* keep backfill worker pool topped up ([069c969](https://github.com/edithatogo/fyi-archive/commit/069c9696a7d0743856db1fc46782ab530aced18f))
* persist updated backfill state ([5c153d0](https://github.com/edithatogo/fyi-archive/commit/5c153d02bb60081e992b9b9315e556d1d925fe79))
* restore valid backfill schedule ([900da25](https://github.com/edithatogo/fyi-archive/commit/900da25f73c1fa9fbcf235b5bf5a304d70ecb2f5))
* satisfy backfill verification type checks ([43464c3](https://github.com/edithatogo/fyi-archive/commit/43464c39a3b706a606d1f5950d46b91683369b30))

## [0.5.0](https://github.com/edithatogo/fyi-archive/compare/fyi_archive-v0.4.0...fyi_archive-v0.5.0) (2026-07-03)


### Features

* report backfill publication verification ([47a83fc](https://github.com/edithatogo/fyi-archive/commit/47a83fc86b5090b2b29aac8a30f236d675a13c5f))


### Bug Fixes

* allow empty verified backfill merges ([62ac7e5](https://github.com/edithatogo/fyi-archive/commit/62ac7e53e89c00b84c02d761bcf471362311ffb5))
* bound historical backfill chunk runtime ([061a649](https://github.com/edithatogo/fyi-archive/commit/061a64938f8fb07062d4173bb4db05fabec048a5))
* filter cumulative backfill publication artifacts ([8f24ea4](https://github.com/edithatogo/fyi-archive/commit/8f24ea4dec605dd6b31ae11ed6b839d7f06cda1b))
* include backfill state helper ([56b5765](https://github.com/edithatogo/fyi-archive/commit/56b576555e17d2a84ffec52a7d4644a396a0ca1f))
* load historical backfill controller state issue ([02e8c88](https://github.com/edithatogo/fyi-archive/commit/02e8c88bdc6b2aa09cd15cfb1d93427fc901cefb))
* mark merged controller batch labels ([28b16f5](https://github.com/edithatogo/fyi-archive/commit/28b16f54ab814159650016c2ef9c3961139db786))
* paginate merge artifact discovery ([1030cde](https://github.com/edithatogo/fyi-archive/commit/1030cde3fd88ca16299570626efac9183de91a8d))
* persist verified backfill merge state ([c677dfd](https://github.com/edithatogo/fyi-archive/commit/c677dfd2d76eb2cd9b3027bfec7c41c2e66befd7))
* publish cumulative merged archive ([940745a](https://github.com/edithatogo/fyi-archive/commit/940745ab27e174ae5322aa7c76dec91a27b20003))
* publish from merged archive artifacts ([43f42bf](https://github.com/edithatogo/fyi-archive/commit/43f42bfce7b210330e9c50a643c70e403c92b28c))
* run historical backfill continuously ([fde869c](https://github.com/edithatogo/fyi-archive/commit/fde869c7c3aa26fe0d714dac9469431398fd627b))
* serialize backfill state merges ([dd6fbf9](https://github.com/edithatogo/fyi-archive/commit/dd6fbf97da29de79153add8085c222c5453c8960))
* skip backfill dispatch while workers are active ([f868045](https://github.com/edithatogo/fyi-archive/commit/f86804537ad676e70f6ea59c1d5a24c28ee1eeab))


### Documentation

* update archive mirror metadata ([ab15cf4](https://github.com/edithatogo/fyi-archive/commit/ab15cf438ea993580075bf16f650f27ad007220f))

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
