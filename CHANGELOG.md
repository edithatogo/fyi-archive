# Changelog

All notable changes to this project are documented here.

This file is managed by `release-please` from Conventional Commits after the initial
bootstrap release.

## [0.16.0](https://github.com/edithatogo/fyi-archive/compare/fyi_archive-v0.15.2...fyi_archive-v0.16.0) (2026-07-24)


### Features

* add separate recurring FOI site snapshots ([dfef793](https://github.com/edithatogo/fyi-archive/commit/dfef793b39843aff07598d76d5d09402d8e2c09d))
* implement remaining archive readiness contracts ([283654a](https://github.com/edithatogo/fyi-archive/commit/283654ae6c1011280771030c7803a883e3d9b859))


### Bug Fixes

* **ci:** authenticate Codecov with OIDC ([deef659](https://github.com/edithatogo/fyi-archive/commit/deef659388772b861b70860d84cc000bdb57e20c))
* type historical archive helpers ([15ee321](https://github.com/edithatogo/fyi-archive/commit/15ee32131751bf51277000783c75b1711ee0b6a3))

## [0.15.2](https://github.com/edithatogo/fyi-archive/compare/fyi_archive-v0.15.1...fyi_archive-v0.15.2) (2026-07-24)


### Bug Fixes

* align CDX paginator with archive query shape ([42208c1](https://github.com/edithatogo/fyi-archive/commit/42208c133aabe1595dd778686fd65d9d157aba0f))
* fall back when CDX page count is null ([a78fc17](https://github.com/edithatogo/fyi-archive/commit/a78fc1750b733f1bb41f047f97ffd6aff4bf93b8))
* paginate Internet Archive CDX inventories ([fe354e2](https://github.com/edithatogo/fyi-archive/commit/fe354e27441ca53770b0ac497712d97c31eeee8b))
* use compatible CDX wildcard query ([ec18937](https://github.com/edithatogo/fyi-archive/commit/ec189379ce17d04ae5d3b23b718f04a58988d4e5))
* use wildcard CDX scope for pagination ([1a34a24](https://github.com/edithatogo/fyi-archive/commit/1a34a24e363d537bf1d49dd3621626ff94fb7c1d))

## [0.15.1](https://github.com/edithatogo/fyi-archive/compare/fyi_archive-v0.15.0...fyi_archive-v0.15.1) (2026-07-21)


### Bug Fixes

* bound live fyi-cli capture subprocesses ([a2b57a6](https://github.com/edithatogo/fyi-archive/commit/a2b57a646ea4773b582098dd8db08d39cd245591))
* bound live fyi-cli capture subprocesses ([#220](https://github.com/edithatogo/fyi-archive/issues/220)) ([7d6a2b4](https://github.com/edithatogo/fyi-archive/commit/7d6a2b409397636de1dcbb38ba57f791c7960b63))
* make capture timeouts terminal ([780a8c3](https://github.com/edithatogo/fyi-archive/commit/780a8c3d584f4f3f7438021c7278c8a50d2c5457))
* make capture timeouts terminal ([#222](https://github.com/edithatogo/fyi-archive/issues/222)) ([f249df0](https://github.com/edithatogo/fyi-archive/commit/f249df0eb3ad84286f93e12e026b1e15d24a3a80))
* resolve canonical live request slugs ([79c9cc9](https://github.com/edithatogo/fyi-archive/commit/79c9cc942aa49762099c0d7b35848f006a011305))
* resolve canonical live request slugs ([#223](https://github.com/edithatogo/fyi-archive/issues/223)) ([090fdfb](https://github.com/edithatogo/fyi-archive/commit/090fdfb3aeef40fc2500dc439bc6bcc8615c7c7d))
* terminate timed out capture process trees ([ead77ba](https://github.com/edithatogo/fyi-archive/commit/ead77ba6a2313e3e734d17cd2c8127fa1cdf382e))

## [0.15.0](https://github.com/edithatogo/fyi-archive/compare/fyi_archive-v0.14.0...fyi_archive-v0.15.0) (2026-07-21)


### Features

* validate versioned FOI-O derived manifests ([#213](https://github.com/edithatogo/fyi-archive/issues/213)) ([5e835a1](https://github.com/edithatogo/fyi-archive/commit/5e835a1b5195b913a3f6fef260ab7046593cccb8))

## [0.14.0](https://github.com/edithatogo/fyi-archive/compare/fyi_archive-v0.13.0...fyi_archive-v0.14.0) (2026-07-21)


### Features

* refresh HF card from verified sync metadata ([#204](https://github.com/edithatogo/fyi-archive/issues/204)) ([74481da](https://github.com/edithatogo/fyi-archive/commit/74481dab64215a77ae5ee32c722927fddbd26f16))


### Bug Fixes

* allow empty process logs in backfill merges ([#209](https://github.com/edithatogo/fyi-archive/issues/209)) ([ed3154c](https://github.com/edithatogo/fyi-archive/commit/ed3154c3ae31a6a62656fd76c1055c251b26dd4b))
* discover process logs in downloaded artifacts ([#208](https://github.com/edithatogo/fyi-archive/issues/208)) ([16171ba](https://github.com/edithatogo/fyi-archive/commit/16171babd377db9f133defc67918f0c2c1a77156))

## [0.13.0](https://github.com/edithatogo/fyi-archive/compare/fyi_archive-v0.12.0...fyi_archive-v0.13.0) (2026-07-21)


### Features

* add opt-in Sigstore release signing ([#186](https://github.com/edithatogo/fyi-archive/issues/186)) ([a3fdad1](https://github.com/edithatogo/fyi-archive/commit/a3fdad194e08981c1fe4ec41c8b80ffb51bfc2a3))
* consume fyi-cli process event projections ([#198](https://github.com/edithatogo/fyi-archive/issues/198)) ([a5efdc8](https://github.com/edithatogo/fyi-archive/commit/a5efdc8857291653090b5de30e5a5383140c1ce6))


### Bug Fixes

* map fyi-cli logical request ids ([#201](https://github.com/edithatogo/fyi-archive/issues/201)) ([2fe6279](https://github.com/edithatogo/fyi-archive/commit/2fe62791a3ea62842978c86701fb4d5f1f9fa9e3))
* normalize live capture directory ids ([#199](https://github.com/edithatogo/fyi-archive/issues/199)) ([99b0b2e](https://github.com/edithatogo/fyi-archive/commit/99b0b2ef96b63be824e7e8bfdae4b359f00c257b))
* pin fyi-cli exporter commit ([#203](https://github.com/edithatogo/fyi-archive/issues/203)) ([5370f92](https://github.com/edithatogo/fyi-archive/commit/5370f92ed6e4a257a9ee52bd06657e117770fdfe))

## [0.12.0](https://github.com/edithatogo/fyi-archive/compare/fyi_archive-v0.11.1...fyi_archive-v0.12.0) (2026-07-14)


### Features

* adopt FOI-O capability declarations ([#191](https://github.com/edithatogo/fyi-archive/issues/191)) ([192b981](https://github.com/edithatogo/fyi-archive/commit/192b9816314fbaaeca4e464215bd2e74bb255f03))


### Documentation

* refresh health evidence status ([#184](https://github.com/edithatogo/fyi-archive/issues/184)) ([70d58d5](https://github.com/edithatogo/fyi-archive/commit/70d58d5358b433d42d7fc8e6d7a7a6d6916697d7))

## [0.11.1](https://github.com/edithatogo/fyi-archive/compare/fyi_archive-v0.11.0...fyi_archive-v0.11.1) (2026-07-13)


### Bug Fixes

* verify selected Zenodo mirror independently ([#183](https://github.com/edithatogo/fyi-archive/issues/183)) ([b8cf5ce](https://github.com/edithatogo/fyi-archive/commit/b8cf5cefe22046237650b957c578f088f0e7abaa))


### Documentation

* update Zenodo DOI citation ([#181](https://github.com/edithatogo/fyi-archive/issues/181)) ([e283682](https://github.com/edithatogo/fyi-archive/commit/e283682a88f7a119e9c06390521b7d8515d2dad7))

## [0.11.0](https://github.com/edithatogo/fyi-archive/compare/fyi_archive-v0.10.6...fyi_archive-v0.11.0) (2026-07-13)


### Features

* expose coverage progress in health reports ([#179](https://github.com/edithatogo/fyi-archive/issues/179)) ([5cfa640](https://github.com/edithatogo/fyi-archive/commit/5cfa6407789bc48ce4ee632a0dcedf66cd7717f3))

## [0.10.6](https://github.com/edithatogo/fyi-archive/compare/fyi_archive-v0.10.5...fyi_archive-v0.10.6) (2026-07-13)


### Documentation

* refresh operational evidence status ([d11d429](https://github.com/edithatogo/fyi-archive/commit/d11d429ee7b9358ba33ae42ccfd6ce99ff3fccf6))
* refresh operational evidence status ([c94f686](https://github.com/edithatogo/fyi-archive/commit/c94f68636aab132fa06ca2d197c636eb3e66536e))

## [0.10.5](https://github.com/edithatogo/fyi-archive/compare/fyi_archive-v0.10.4...fyi_archive-v0.10.5) (2026-07-13)


### Bug Fixes

* isolate OSF workflow verification target ([ccab5d8](https://github.com/edithatogo/fyi-archive/commit/ccab5d89c6e18fa87de14b000013360ce0b323cf))
* isolate OSF workflow verification target ([536a049](https://github.com/edithatogo/fyi-archive/commit/536a04969c4ed2b5a51545b2385a752e6bafc49e))
* isolate targeted mirror verification ([8fa44ec](https://github.com/edithatogo/fyi-archive/commit/8fa44eccdfb05de3bfb63c3be956e60ffd790af8))
* isolate targeted mirror verification ([db60baa](https://github.com/edithatogo/fyi-archive/commit/db60baadad4b6707ab8a02ccc61ec103fe078fe3))
* retry eventual OSF listing consistency ([ce8f639](https://github.com/edithatogo/fyi-archive/commit/ce8f639c689cbdb3591d92967fb6b3898f4321d6))
* retry eventual OSF listing consistency ([1161c4d](https://github.com/edithatogo/fyi-archive/commit/1161c4d2bff2b7b5a1d6d742ddd551964f230e49))

## [0.10.4](https://github.com/edithatogo/fyi-archive/compare/fyi_archive-v0.10.3...fyi_archive-v0.10.4) (2026-07-13)


### Documentation

* record OSF verification outcome ([eca9b00](https://github.com/edithatogo/fyi-archive/commit/eca9b00ba3f9421f041a8900b4b9e0ff4f23749e))

## [0.10.3](https://github.com/edithatogo/fyi-archive/compare/fyi_archive-v0.10.2...fyi_archive-v0.10.3) (2026-07-12)


### Documentation

* **conductor:** close remaining source tracks ([10fc3ee](https://github.com/edithatogo/fyi-archive/commit/10fc3ee92b4d6fa0d2f72b334dce9903b2cb4c1a))
* **conductor:** close remaining source tracks ([5e9c175](https://github.com/edithatogo/fyi-archive/commit/5e9c1751f04b9c87a75d3c589cbc57049442e2ea))

## [0.10.2](https://github.com/edithatogo/fyi-archive/compare/fyi_archive-v0.10.1...fyi_archive-v0.10.2) (2026-07-12)


### Documentation

* close feed assessment with bounded evidence ([03c1aeb](https://github.com/edithatogo/fyi-archive/commit/03c1aebc3972ce38e07517bc7ee9cc070f0fc1ae))

## [0.10.1](https://github.com/edithatogo/fyi-archive/compare/fyi_archive-v0.10.0...fyi_archive-v0.10.1) (2026-07-12)


### Bug Fixes

* verify explicit live capture evidence ([fca0fc7](https://github.com/edithatogo/fyi-archive/commit/fca0fc709f2f79d76acc5f792e9e35f6f2f85bfa))


### Documentation

* record all working-site smoke outcomes ([841e7f4](https://github.com/edithatogo/fyi-archive/commit/841e7f41b9b697404b810b1bb851469d48239a55))
* record verified Uruguay live smoke ([acf317f](https://github.com/edithatogo/fyi-archive/commit/acf317fbae683f31f93e1363b8a46e78b9c22f55))

## [0.10.0](https://github.com/edithatogo/fyi-archive/compare/fyi_archive-v0.9.0...fyi_archive-v0.10.0) (2026-07-12)


### Features

* support explicit request references ([c6c89b8](https://github.com/edithatogo/fyi-archive/commit/c6c89b8be8d761b055bb5dfdfcc69cca3bce4818))
* support explicit request references ([af90073](https://github.com/edithatogo/fyi-archive/commit/af900733b8ac733b6c32b170f3b8a811a006af18))


### Bug Fixes

* assemble live manifests from captured requests ([996ca2d](https://github.com/edithatogo/fyi-archive/commit/996ca2dc5d42541aa8b2a4af9571c050bda6b769))
* assemble live manifests from captured requests ([ea8d620](https://github.com/edithatogo/fyi-archive/commit/ea8d6209ffe2e75898cad42787f9603189c74f67))
* enforce seed interval outside fyi-cli ([b9095ad](https://github.com/edithatogo/fyi-archive/commit/b9095adc18c93340736cd7f351883ed68011546f))
* fall back when request discovery is empty ([a8f94f0](https://github.com/edithatogo/fyi-archive/commit/a8f94f02e59917ebad182599b845afd715c43d65))
* **workflow:** allow explicit live smoke outside window ([54f2896](https://github.com/edithatogo/fyi-archive/commit/54f28969cce6cdcfc4b9831096ed3a96104a7b22))
* **workflow:** allow explicit live smoke outside window ([8c15437](https://github.com/edithatogo/fyi-archive/commit/8c15437fb3d3c928b55b4773881a05feda5b8a26))
* **workflow:** enable catalog fallback for live sites ([19af11d](https://github.com/edithatogo/fyi-archive/commit/19af11d0cedaa444870a5e04db00f99336904c63))
* **workflow:** enable catalog fallback for live sites ([62f7f71](https://github.com/edithatogo/fyi-archive/commit/62f7f713b6e11fe1242827149c1df58f7d32c98f))

## [0.9.0](https://github.com/edithatogo/fyi-archive/compare/fyi_archive-v0.8.0...fyi_archive-v0.9.0) (2026-07-12)


### Features

* add gentle archives for working Alaveteli sites ([#132](https://github.com/edithatogo/fyi-archive/issues/132)) ([dd76cf7](https://github.com/edithatogo/fyi-archive/commit/dd76cf7557990b2e841de2e4d11593d1ba178fb8))
* add historical Alaveteli source modes ([#136](https://github.com/edithatogo/fyi-archive/issues/136)) ([d58c51c](https://github.com/edithatogo/fyi-archive/commit/d58c51c49bfb1c54af7b34044aa56b8c1fa277ad))
* add structured historical source adapters ([5bbbe08](https://github.com/edithatogo/fyi-archive/commit/5bbbe089b02649e33092b1d7d39803e1e7ebf20b))
* automate Alaveteli feed compatibility probes ([2069e30](https://github.com/edithatogo/fyi-archive/commit/2069e30f5008afd884c50f5b3a02270e6bd685b6))
* automate historical source indexes ([#129](https://github.com/edithatogo/fyi-archive/issues/129)) ([b2c32fd](https://github.com/edithatogo/fyi-archive/commit/b2c32fd4b2b87048f317b29b183e601d8b857408))
* enrich historical Alaveteli core data ([#138](https://github.com/edithatogo/fyi-archive/issues/138)) ([f50b748](https://github.com/edithatogo/fyi-archive/commit/f50b748d4ecd9e05feb5a868cc2cd7c75d32d5ab))
* schedule bounded overnight live smokes ([#135](https://github.com/edithatogo/fyi-archive/issues/135)) ([c29e972](https://github.com/edithatogo/fyi-archive/commit/c29e9720360afb2c5ce91d5763318cc6fdce77e8))


### Bug Fixes

* bound historical replay enrichment time ([#140](https://github.com/edithatogo/fyi-archive/issues/140)) ([a1d6116](https://github.com/edithatogo/fyi-archive/commit/a1d611675edc89ccb470c6e81566ddf12599bb96))
* enforce local overnight capture windows ([#134](https://github.com/edithatogo/fyi-archive/issues/134)) ([ed2b2de](https://github.com/edithatogo/fyi-archive/commit/ed2b2de563da9680ab049fe45a31b6577f3c5fda))
* record delayed live smoke windows ([#141](https://github.com/edithatogo/fyi-archive/issues/141)) ([730df70](https://github.com/edithatogo/fyi-archive/commit/730df705f236b62a53e8b9ee824cab7bf4629455))
* use Morph data table in index query ([#131](https://github.com/edithatogo/fyi-archive/issues/131)) ([3c3c7a7](https://github.com/edithatogo/fyi-archive/commit/3c3c7a7f316137e2a04ccabe0526a3b70fbf1592))


### Documentation

* record full historical core enrichment ([#142](https://github.com/edithatogo/fyi-archive/issues/142)) ([6bde467](https://github.com/edithatogo/fyi-archive/commit/6bde4672f84ef7642e6fbeb103bfbb3d09f02481))
* record historical core-data smoke ([#139](https://github.com/edithatogo/fyi-archive/issues/139)) ([52dc9a8](https://github.com/edithatogo/fyi-archive/commit/52dc9a8e77472dd611eccd1b48ac5c6837da0e0a))
* record historical index evidence ([#137](https://github.com/edithatogo/fyi-archive/issues/137)) ([9f44ff0](https://github.com/edithatogo/fyi-archive/commit/9f44ff0dd4d7a5184c53f5831e44b79d58705b9e))
* record working Alaveteli dry-run evidence ([#133](https://github.com/edithatogo/fyi-archive/issues/133)) ([185673e](https://github.com/edithatogo/fyi-archive/commit/185673e959871560bab2a6fe5b902efac1e608c6))

## [0.8.0](https://github.com/edithatogo/fyi-archive/compare/fyi_archive-v0.7.0...fyi_archive-v0.8.0) (2026-07-11)


### Features

* add provenance-preserving AU catalog fallback ([#114](https://github.com/edithatogo/fyi-archive/issues/114)) ([a5489ec](https://github.com/edithatogo/fyi-archive/commit/a5489ec303c956ca5ce37a22b38e11ef0794d184))
* **au:** add jurisdiction rollout controller ([70da7b7](https://github.com/edithatogo/fyi-archive/commit/70da7b7e556c0077160de97e2d3488a0539ea7ea))
* **au:** add jurisdiction rollout controller ([723659a](https://github.com/edithatogo/fyi-archive/commit/723659afca3b59088336f21f56928bff52917075))
* **au:** add NSW historical seed workflow and test harness ([b128ebe](https://github.com/edithatogo/fyi-archive/commit/b128ebe64a6cd4a562ecc8b6107329bb5de3a3e1))
* automate instance-scoped publication and project sync ([#116](https://github.com/edithatogo/fyi-archive/issues/116)) ([eb24516](https://github.com/edithatogo/fyi-archive/commit/eb2451687c476811a7cc625bc6ce40cdb4b0f213))


### Bug Fixes

* align AU controller dry run with CLI ([#121](https://github.com/edithatogo/fyi-archive/issues/121)) ([e954662](https://github.com/edithatogo/fyi-archive/commit/e954662930a3fa5e3b97514c0d279810fc1a4898))
* **au:** harden body discovery and NSW CSV parsing ([8ffd3fd](https://github.com/edithatogo/fyi-archive/commit/8ffd3fdd5ebcb421ed17d7d9e140b687bdc0ceb3))
* **au:** harden body discovery and NSW CSV parsing ([5d83629](https://github.com/edithatogo/fyi-archive/commit/5d83629fef87980531705cb0780f154786cb710d))
* **au:** normalize NSW authority queue keys ([453d08f](https://github.com/edithatogo/fyi-archive/commit/453d08fc4fc8dc483af0c1476bc29f14408021bb))
* **au:** normalize NSW authority queue keys ([114454b](https://github.com/edithatogo/fyi-archive/commit/114454b89bfd27a5d713bb203c71fbacc3f73e87))
* generalize readme and retain live catalogs ([#120](https://github.com/edithatogo/fyi-archive/issues/120)) ([ff2a8b2](https://github.com/edithatogo/fyi-archive/commit/ff2a8b2346e3203896b8abed7cfa722b6734b6c3))
* keep publication dry runs offline ([#123](https://github.com/edithatogo/fyi-archive/issues/123)) ([86bde5e](https://github.com/edithatogo/fyi-archive/commit/86bde5e5a83be7e3ea4adf96a4173da7ed8795e8))
* make publication dry runs network independent ([#122](https://github.com/edithatogo/fyi-archive/issues/122)) ([111f1ac](https://github.com/edithatogo/fyi-archive/commit/111f1aca32266d34aaa87e7ecbc5326c3a807ca9))
* require explicit confirmation for AU live capture ([#125](https://github.com/edithatogo/fyi-archive/issues/125)) ([ff5be8a](https://github.com/edithatogo/fyi-archive/commit/ff5be8a5307151551affe289d7e063da3e9e861a))
* scope health monitoring by archive instance ([#118](https://github.com/edithatogo/fyi-archive/issues/118)) ([7d19522](https://github.com/edithatogo/fyi-archive/commit/7d1952283f9bac39a05489a98eb913da5d88fc22))
* **workflow:** create NSW seed output directory ([bc48c5b](https://github.com/edithatogo/fyi-archive/commit/bc48c5b46e483288b731c5f19aaa106b1398d94b))
* **workflow:** create NSW seed output directory ([ace4eb7](https://github.com/edithatogo/fyi-archive/commit/ace4eb7f4643d59f6652e908c5719a1f04b2d728))
* **workflow:** match seed CLI options ([14eced1](https://github.com/edithatogo/fyi-archive/commit/14eced1dc8baf9d65589e1985b92aa2e81d8df4d))
* **workflow:** match seed CLI options ([8163866](https://github.com/edithatogo/fyi-archive/commit/8163866b9024c9e7e9c56eac89d3b1f1ac35d29c))
* **workflow:** use explicit NSW queue guard ([1496f60](https://github.com/edithatogo/fyi-archive/commit/1496f60a136bf1574e884061042b0160563e2d1e))
* **workflow:** use explicit NSW queue guard ([2f3ae1a](https://github.com/edithatogo/fyi-archive/commit/2f3ae1a5c188641180fafbcd177ba586388c03c4))


### Documentation

* add safe global instance onboarding templates ([#117](https://github.com/edithatogo/fyi-archive/issues/117)) ([49a290c](https://github.com/edithatogo/fyi-archive/commit/49a290c14784998c0db6f951cd69d9251096193d))
* **conductor:** complete AU NSW seed track ([2e2d0e7](https://github.com/edithatogo/fyi-archive/commit/2e2d0e7e591b8746cc4eec6e9a49c084d651d6eb))
* **conductor:** complete AU NSW seed track ([f088ecc](https://github.com/edithatogo/fyi-archive/commit/f088eccec60470085dc0cf658b7b75bf5cad6aa0))
* **conductor:** record AU rollout controller progress ([91fb5df](https://github.com/edithatogo/fyi-archive/commit/91fb5dfd5ffb096d91ca6140337a32cdaf02c5b4))
* **conductor:** record AU rollout controller progress ([6469f0b](https://github.com/edithatogo/fyi-archive/commit/6469f0ba17d7671e634c907f8bd78532f1194945))
* record owner branch protection exception ([#127](https://github.com/edithatogo/fyi-archive/issues/127)) ([1258bab](https://github.com/edithatogo/fyi-archive/commit/1258bab05f187cc4038cb4dc2499e6dc4c295064))
* sync completed conductor acceptance checklists ([#119](https://github.com/edithatogo/fyi-archive/issues/119)) ([64eda80](https://github.com/edithatogo/fyi-archive/commit/64eda80386b973b1be8f5e7368ce357860a967f0))

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
