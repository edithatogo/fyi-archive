"""Archive instance registry (orchestration config; capture stays in fyi-cli)."""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_INSTANCE_ID = "nz-fyi"


@dataclass(frozen=True, slots=True)
class ArchiveInstance:
    """One Alaveteli site archive configuration."""

    id: str
    base_url: str
    country: str
    locale: str
    hf_repo_id: str
    rate_limit_name: str
    status: str
    title: str
    source: str
    catalog_url: str | None = None
    source_modes: tuple[str, ...] = ("live_api", "atom_feed", "internet_archive")
    seed_cap: int = 1000

    def capture_base_url(self) -> str:
        """Return base URL without trailing slash for fyi-cli --base-url."""
        return self.base_url.rstrip("/")

    def search_feed_url(self) -> str:
        """Return fyi-cli's read-only Alaveteli JSON search-feed entry point."""
        return f"{self.capture_base_url()}/search/all?output=json&page=1"


_INSTANCES: dict[str, ArchiveInstance] = {
    "nz-fyi": ArchiveInstance(
        id="nz-fyi",
        base_url="https://fyi.org.nz",
        country="NZ",
        locale="en-NZ",
        hf_repo_id="edithatogo/fyi-archive-nz",
        rate_limit_name="archive-discovery-nz-fyi",
        status="supported",
        title="fyi-archive (fyi.org.nz OIA register)",
        source="https://fyi.org.nz/",
        catalog_url="https://fyi.org.nz/body/all-authorities.csv",
        source_modes=("live_api", "atom_feed", "authority_catalog", "internet_archive"),
    ),
    "au-rtk": ArchiveInstance(
        id="au-rtk",
        base_url="https://www.righttoknow.org.au",
        country="AU",
        locale="en-AU",
        hf_repo_id="edithatogo/rtk-archive-au",
        rate_limit_name="archive-discovery-au-rtk",
        status="experimental",
        title="rtk-archive (righttoknow.org.au FOI register)",
        source="https://www.righttoknow.org.au/",
        catalog_url="https://www.righttoknow.org.au/body/all-authorities.csv",
        source_modes=("live_api", "atom_feed", "authority_catalog", "internet_archive"),
    ),
    "uk-wdtk": ArchiveInstance(
        id="uk-wdtk",
        base_url="https://www.whatdotheyknow.com",
        country="GB",
        locale="en-GB",
        hf_repo_id="edithatogo/wdtk-archive-uk",
        rate_limit_name="archive-discovery-uk-wdtk",
        status="experimental",
        title="wdtk-archive (whatdotheyknow.com FOI register)",
        source="https://www.whatdotheyknow.com/",
        catalog_url="https://www.whatdotheyknow.com/body/all-authorities.csv",
        source_modes=("live_api", "atom_feed", "authority_catalog", "internet_archive"),
    ),
    "ie-myrighttoknow": ArchiveInstance(
        id="ie-myrighttoknow",
        base_url="https://www.myrighttoknow.org",
        country="IE",
        locale="en-IE",
        hf_repo_id="edithatogo/mrtk-archive-ie",
        rate_limit_name="archive-discovery-ie-myrighttoknow",
        status="experimental",
        title="mrtk-archive (myrighttoknow.org FOI register)",
        source="https://www.myrighttoknow.org/",
        catalog_url="https://www.myrighttoknow.org/body/all-authorities.csv",
        source_modes=("live_api", "atom_feed", "authority_catalog", "internet_archive"),
    ),
    "se-handlingar": ArchiveInstance(
        id="se-handlingar",
        base_url="https://handlingar.se",
        country="SE",
        locale="sv-SE",
        hf_repo_id="edithatogo/handlingar-archive-se",
        rate_limit_name="archive-discovery-se-handlingar",
        status="experimental",
        title="handlingar.se public-records register",
        source="https://handlingar.se/",
        catalog_url="https://handlingar.se/body/all-authorities.csv",
        source_modes=("live_api", "atom_feed", "authority_catalog", "internet_archive"),
    ),
    "ua-dostup": ArchiveInstance(
        id="ua-dostup",
        base_url="https://dostup.org.ua",
        country="UA",
        locale="uk-UA",
        hf_repo_id="edithatogo/dostup-archive-ua",
        rate_limit_name="archive-discovery-ua-dostup",
        status="experimental",
        title="Доступ до правди public-records register",
        source="https://dostup.org.ua/",
        catalog_url="https://dostup.org.ua/body/all-authorities.csv",
        source_modes=("live_api", "atom_feed", "authority_catalog", "internet_archive"),
    ),
    "uy-quesabes": ArchiveInstance(
        id="uy-quesabes",
        base_url="https://quesabes.org",
        country="UY",
        locale="es-UY",
        hf_repo_id="edithatogo/quesabes-archive-uy",
        rate_limit_name="archive-discovery-uy-quesabes",
        status="experimental",
        title="Qué Sabés public-information register",
        source="https://quesabes.org/",
        catalog_url="https://quesabes.org/body/all-authorities.csv",
        source_modes=("live_api", "atom_feed", "authority_catalog", "internet_archive"),
    ),
    "ge-askgov": ArchiveInstance(
        id="ge-askgov",
        base_url="https://askgov.ge",
        country="GE",
        locale="ka-GE",
        hf_repo_id="edithatogo/askgov-archive-ge",
        rate_limit_name="archive-discovery-ge-askgov",
        status="experimental",
        title="Ask Gov Georgia public-information register",
        source="https://askgov.ge/",
        catalog_url="https://askgov.ge/body/all-authorities.csv",
        source_modes=("live_api", "atom_feed", "authority_catalog", "internet_archive"),
    ),
    "eu-asktheeu": ArchiveInstance(
        id="eu-asktheeu",
        base_url="https://www.asktheeu.org",
        country="EU",
        locale="en-EU",
        hf_repo_id="edithatogo/asktheeu-archive-eu",
        rate_limit_name="archive-discovery-eu-asktheeu",
        status="historical-only",
        title="AskTheEU public-information register",
        source="https://www.asktheeu.org/",
        source_modes=("atom_feed", "internet_archive", "official_dataset", "operator_export"),
    ),
    "cz-infoprovsechny": ArchiveInstance(
        id="cz-infoprovsechny",
        base_url="https://www.infoprovsechny.cz",
        country="CZ",
        locale="cs-CZ",
        hf_repo_id="edithatogo/infoprovsechny-archive-cz",
        rate_limit_name="archive-discovery-cz-infoprovsechny",
        status="historical-only",
        title="Info Pro Všechny public-information register",
        source="https://www.infoprovsechny.cz/",
        source_modes=("atom_feed", "internet_archive", "official_dataset", "operator_export"),
    ),
    "fr-madada": ArchiveInstance(
        id="fr-madada",
        base_url="https://madada.fr",
        country="FR",
        locale="fr-FR",
        hf_repo_id="edithatogo/madada-archive-fr",
        rate_limit_name="archive-discovery-fr-madada",
        status="historical-only",
        title="MaDada public-information register",
        source="https://madada.fr/",
        source_modes=("atom_feed", "internet_archive", "official_dataset", "operator_export"),
    ),
    "nl-woo-knop": ArchiveInstance(
        id="nl-woo-knop",
        base_url="https://www.woo-knop.nl",
        country="NL",
        locale="nl-NL",
        hf_repo_id="edithatogo/woo-knop-archive-nl",
        rate_limit_name="archive-discovery-nl-woo-knop",
        status="historical-only",
        title="de Woo-Knop public-information register",
        source="https://www.woo-knop.nl/",
        source_modes=("atom_feed", "internet_archive", "official_dataset", "operator_export"),
    ),
    "be-transparencia": ArchiveInstance(
        id="be-transparencia",
        base_url="https://transparencia.be",
        country="BE",
        locale="fr-BE",
        hf_repo_id="edithatogo/transparencia-archive-be",
        rate_limit_name="archive-discovery-be-transparencia",
        status="historical-only",
        title="Transparencia public-information register",
        source="https://transparencia.be/",
        source_modes=("atom_feed", "internet_archive", "official_dataset", "operator_export"),
    ),
    "hr-imamopravoznati": ArchiveInstance(
        id="hr-imamopravoznati",
        base_url="https://imamopravoznati.org",
        country="HR",
        locale="hr-HR",
        hf_repo_id="edithatogo/imamopravoznati-archive-hr",
        rate_limit_name="archive-discovery-hr-imamopravoznati",
        status="historical-only",
        title="Imamo pravo znati public-information register",
        source="https://imamopravoznati.org/",
        source_modes=("atom_feed", "internet_archive", "official_dataset", "operator_export"),
    ),
    "hu-kimittud": ArchiveInstance(
        id="hu-kimittud",
        base_url="https://kimittud.hu",
        country="HU",
        locale="hu-HU",
        hf_repo_id="edithatogo/kimittud-archive-hu",
        rate_limit_name="archive-discovery-hu-kimittud",
        status="historical-only",
        title="Ki Mit Tud public-information register",
        source="https://kimittud.hu/",
        source_modes=("atom_feed", "internet_archive", "official_dataset", "operator_export"),
    ),
    "gr-arthro5a": ArchiveInstance(
        id="gr-arthro5a",
        base_url="https://www.arthro5a.gr",
        country="GR",
        locale="el-GR",
        hf_repo_id="edithatogo/arthro5a-archive-gr",
        rate_limit_name="archive-discovery-gr-arthro5a",
        status="historical-only",
        title="arthro5A public-information register",
        source="https://www.arthro5a.gr/",
        source_modes=("atom_feed", "internet_archive", "official_dataset", "operator_export"),
    ),
    "md-vreauinfo": ArchiveInstance(
        id="md-vreauinfo",
        base_url="https://www.vreauinfo.md",
        country="MD",
        locale="ro-MD",
        hf_repo_id="edithatogo/vreauinfo-archive-md",
        rate_limit_name="archive-discovery-md-vreauinfo",
        status="historical-only",
        title="VreauInfo public-information register",
        source="https://www.vreauinfo.md/",
        source_modes=("atom_feed", "internet_archive", "official_dataset", "operator_export"),
    ),
    "hk-accessinfo": ArchiveInstance(
        id="hk-accessinfo",
        base_url="https://accessinfo.hk",
        country="HK",
        locale="en-HK",
        hf_repo_id="edithatogo/accessinfo-archive-hk",
        rate_limit_name="archive-discovery-hk-accessinfo",
        status="historical-only",
        title="accessinfo.hk public-information register",
        source="https://accessinfo.hk/",
        source_modes=("atom_feed", "internet_archive", "official_dataset", "operator_export"),
    ),
    "lr-infolib": ArchiveInstance(
        id="lr-infolib",
        base_url="https://infolib.org.lr",
        country="LR",
        locale="en-LR",
        hf_repo_id="edithatogo/infolib-archive-lr",
        rate_limit_name="archive-discovery-lr-infolib",
        status="historical-only",
        title="InfoLib public-information register",
        source="https://infolib.org.lr/",
        source_modes=("atom_feed", "internet_archive", "official_dataset", "operator_export"),
    ),
    "co-queremosdatos": ArchiveInstance(
        id="co-queremosdatos",
        base_url="https://www.queremosdatos.co",
        country="CO",
        locale="es-CO",
        hf_repo_id="edithatogo/queremosdatos-archive-co",
        rate_limit_name="archive-discovery-co-queremosdatos",
        status="historical-only",
        title="Queremosdatos public-information register",
        source="https://www.queremosdatos.co/",
        source_modes=("atom_feed", "internet_archive", "official_dataset", "operator_export"),
    ),
    "us-opramachine": ArchiveInstance(
        id="us-opramachine",
        base_url="https://opramachine.com",
        country="US-NJ",
        locale="en-US",
        hf_repo_id="edithatogo/opramachine-archive-us-nj",
        rate_limit_name="archive-discovery-us-opramachine",
        status="historical-only",
        title="OPRA Machine public-information register",
        source="https://opramachine.com/",
        source_modes=("atom_feed", "internet_archive", "official_dataset", "operator_export"),
    ),
    "ro-iastatullaintrebari": ArchiveInstance(
        id="ro-iastatullaintrebari",
        base_url="https://iastatullaintrebari.ro",
        country="RO",
        locale="ro-RO",
        hf_repo_id="edithatogo/iastatullaintrebari-archive-ro",
        rate_limit_name="archive-discovery-ro-iastatullaintrebari",
        status="historical-only",
        title="Ia Statul la Întrebări public-information register",
        source="https://iastatullaintrebari.ro/",
        source_modes=("atom_feed", "internet_archive", "official_dataset", "operator_export"),
    ),
    "xk-dumedite": ArchiveInstance(
        id="xk-dumedite",
        base_url="https://dumedite.org",
        country="XK",
        locale="sq-XK",
        hf_repo_id="edithatogo/dumedite-archive-xk",
        rate_limit_name="archive-discovery-xk-dumedite",
        status="historical-only",
        title="dumeditë public-information register",
        source="https://dumedite.org/",
        source_modes=("atom_feed", "internet_archive", "official_dataset", "operator_export"),
    ),
}


def list_instances() -> list[ArchiveInstance]:
    """Return all registered archive instances in stable id order."""
    return [_INSTANCES[key] for key in sorted(_INSTANCES)]


def get_instance(instance_id: str | None = None) -> ArchiveInstance:
    """Resolve an instance by id (default nz-fyi)."""
    resolved = (instance_id or DEFAULT_INSTANCE_ID).strip()
    try:
        return _INSTANCES[resolved]
    except KeyError as error:
        known = ", ".join(sorted(_INSTANCES))
        msg = f"Unknown archive instance {resolved!r}; known: {known}"
        raise ValueError(msg) from error


def resolve_instance(
    *,
    instance_id: str | None = None,
    base_url: str | None = None,
) -> ArchiveInstance:
    """Resolve instance from id and optional base_url override.

    When ``base_url`` is set, the catalog entry is copied with an overridden URL
    and derived ``source`` (trailing slash). Unknown overrides still require a
    known instance_id for HF/rate-limit identity.
    """
    instance = get_instance(instance_id)
    if base_url is None or not str(base_url).strip():
        env_base = os.environ.get("FYI_ARCHIVE_BASE_URL", "").strip()
        if not env_base:
            return instance
        base_url = env_base

    cleaned = str(base_url).strip().rstrip("/")
    if not cleaned:
        return instance
    source = cleaned + "/"
    return ArchiveInstance(
        id=instance.id,
        base_url=cleaned,
        country=instance.country,
        locale=instance.locale,
        hf_repo_id=instance.hf_repo_id,
        rate_limit_name=instance.rate_limit_name,
        status=instance.status,
        title=instance.title,
        source=source,
        catalog_url=instance.catalog_url,
        source_modes=instance.source_modes,
        seed_cap=instance.seed_cap,
    )


def source_for_instance(instance_id: str | None = None) -> str:
    """Return canonical source URL for an instance."""
    return get_instance(instance_id).source


def known_sources() -> frozenset[str]:
    """Return all catalog source URLs (trailing slash)."""
    return frozenset(item.source for item in _INSTANCES.values())


def instance_id_for_source(source: str) -> str | None:
    """Map a manifest source URL to an instance id when known."""
    normalized = source if source.endswith("/") else f"{source}/"
    for item in _INSTANCES.values():
        if item.source == normalized:
            return item.id
    return None
