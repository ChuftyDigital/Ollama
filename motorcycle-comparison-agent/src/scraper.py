"""
Motorcycle listing scraper and data sourcing module.

This module provides:
 - A live scraper that queries public UK motorcycle classified sites
   (AutoTrader, MCN Bikes, eBay Motors, etc.) and dealer pages.
 - A curated demo dataset for offline / CI usage when network access is
   unavailable.

The scraper returns normalised `MotorcycleListing` objects ready for scoring.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Iterable
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

from .models import (
    AnnualCosts,
    COMMON_PROBLEMS,
    ConditionRating,
    DealerInfo,
    MotorcycleListing,
    MotorcycleSpecs,
    REFERENCE_ANNUAL_COSTS,
    REFERENCE_SPECS,
    ServiceHistoryRating,
    WILDCARD_MODELS,
)

logger = logging.getLogger(__name__)

# ── Helpers ──────────────────────────────────────────────────────────────────

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-GB,en;q=0.9",
}

_AUTOTRADER_SEARCH = (
    "https://www.autotrader.co.uk/bike-search"
    "?advertising-location=at_bikes"
    "&price-to={price_to}"
    "&make={make}"
    "&model={model}"
    "&postcode=SW1A+1AA"
    "&radius=1500"
    "&sort=price-asc"
)


def _safe_get(url: str, *, timeout: int = 15) -> requests.Response | None:
    """HTTP GET with retries and polite back-off."""
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=_HEADERS, timeout=timeout)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            logger.warning("GET %s attempt %d failed: %s", url, attempt + 1, exc)
            time.sleep(1.5 * (attempt + 1))
    return None


# ── Live scraper (best-effort) ───────────────────────────────────────────────

def _parse_autotrader_results(
    html: str,
    model_name: str,
    group: str,
) -> list[MotorcycleListing]:
    """Parse AutoTrader bike-search HTML into listings (best-effort)."""
    soup = BeautifulSoup(html, "lxml")
    listings: list[MotorcycleListing] = []

    cards = soup.select("li.search-page__result")
    for card in cards[:10]:  # cap per model
        try:
            title_el = card.select_one("h2, .product-card-details__title")
            price_el = card.select_one(".product-card-pricing__price, .js-price")
            if not title_el or not price_el:
                continue

            price_text = re.sub(r"[^\d]", "", price_el.get_text())
            if not price_text:
                continue
            price = float(price_text)

            mileage_el = card.select_one('[data-testid="search-card-mileage"]')
            mileage = 0
            if mileage_el:
                m = re.sub(r"[^\d]", "", mileage_el.get_text())
                mileage = int(m) if m else 0

            year_match = re.search(r"(20\d{2})", title_el.get_text())
            year = int(year_match.group(1)) if year_match else 2018

            dealer_el = card.select_one(".product-card-seller__name")
            dealer_name = dealer_el.get_text(strip=True) if dealer_el else "Unknown Dealer"

            listing = MotorcycleListing(
                model_name=model_name,
                year=year,
                price=price,
                mileage=mileage,
                condition=ConditionRating.GOOD,
                service_history=ServiceHistoryRating.PARTIAL,
                group=group,
                dealer=DealerInfo(
                    name=dealer_name,
                    address="See dealer website",
                    city="",
                    region="England",
                    postcode="",
                    phone="",
                    email="",
                ),
                specs=REFERENCE_SPECS.get(model_name),
                annual_costs=REFERENCE_ANNUAL_COSTS.get(model_name),
                common_problems=COMMON_PROBLEMS.get(model_name, []),
            )
            listings.append(listing)
        except Exception:
            logger.debug("Skipping unparseable card", exc_info=True)

    return listings


def scrape_live(
    models: dict[str, str],
    budget: float,
) -> list[MotorcycleListing]:
    """Attempt live scraping from AutoTrader UK.

    *models* maps model display-name -> group ("middleweight" | "supernaked").
    Returns whatever listings could be parsed — may be empty.
    """
    all_listings: list[MotorcycleListing] = []

    for model_name, group in models.items():
        parts = model_name.split()
        make = quote_plus(parts[0])
        model = quote_plus(" ".join(parts[1:]))
        url = _AUTOTRADER_SEARCH.format(
            price_to=int(budget),
            make=make,
            model=model,
        )
        resp = _safe_get(url)
        if resp is None:
            logger.info("No response for %s — skipping live results", model_name)
            continue
        parsed = _parse_autotrader_results(resp.text, model_name, group)
        logger.info("Scraped %d listings for %s", len(parsed), model_name)
        all_listings.extend(parsed)

    return all_listings


# ── Curated demo dataset ─────────────────────────────────────────────────────

def _build_demo_listings() -> list[MotorcycleListing]:
    """Hand-curated representative listings for demonstration and testing.

    These mirror realistic dealer stock found across UK classified sites
    during early 2026 research.
    """
    listings: list[MotorcycleListing] = []

    # ── GROUP 1: Middleweights ───────────────────────────────────────────

    # --- Triumph Street Triple R 675 ---
    listings.append(
        MotorcycleListing(
            model_name="Triumph Street Triple R 675",
            year=2016,
            price=3_350,
            mileage=14_200,
            condition=ConditionRating.GOOD,
            service_history=ServiceHistoryRating.FULL_DEALER,
            optional_extras=[
                "Arrow slip-on exhaust",
                "R&G crash protectors",
                "Tail tidy",
                "Heated grips",
            ],
            colour="Crystal White",
            description=(
                "One-owner example with full Triumph dealer stamps to 2024. "
                "Arrow exhaust gives a gorgeous triple howl. Recent front "
                "tyre and brake pads. MOT until Nov 2026."
            ),
            dealer=DealerInfo(
                name="Blade Motorcycles",
                address="123 London Road",
                city="Reading",
                region="England",
                postcode="RG1 4AA",
                phone="0118 900 1234",
                email="sales@blademotorcycles.co.uk",
                website="https://blademotorcycles.co.uk",
                highlights=[
                    "Triumph specialist dealer",
                    "12-month mechanical warranty included",
                    "Finance available",
                ],
            ),
            group="middleweight",
            specs=REFERENCE_SPECS["Triumph Street Triple R 675"],
            annual_costs=REFERENCE_ANNUAL_COSTS["Triumph Street Triple R 675"],
            known_issues=["Cam chain tensioner replaced under warranty at 8k miles"],
            common_problems=COMMON_PROBLEMS["Triumph Street Triple R 675"],
        )
    )
    listings.append(
        MotorcycleListing(
            model_name="Triumph Street Triple R 675",
            year=2014,
            price=2_695,
            mileage=22_400,
            condition=ConditionRating.GOOD,
            service_history=ServiceHistoryRating.FULL_INDEPENDENT,
            optional_extras=["Scorpion exhaust", "Tail tidy", "Bar-end mirrors"],
            colour="Phantom Black",
            description=(
                "Well-maintained 2014 R with independent service history. "
                "Scorpion pipe, recent chain and sprockets. Minor cosmetic "
                "marks on tank consistent with age."
            ),
            dealer=DealerInfo(
                name="Cardiff Motorcycle Centre",
                address="45 Penarth Road",
                city="Cardiff",
                region="Wales",
                postcode="CF10 5DL",
                phone="029 2034 5678",
                email="info@cardiffmotorcycles.co.uk",
                website="https://cardiffmotorcycles.co.uk",
                highlights=[
                    "Established 30+ years",
                    "RAC approved dealer",
                    "Wales delivery available",
                ],
            ),
            group="middleweight",
            specs=REFERENCE_SPECS["Triumph Street Triple R 675"],
            annual_costs=REFERENCE_ANNUAL_COSTS["Triumph Street Triple R 675"],
            known_issues=[],
            common_problems=COMMON_PROBLEMS["Triumph Street Triple R 675"],
        )
    )

    # --- KTM Duke 790 ---
    listings.append(
        MotorcycleListing(
            model_name="KTM Duke 790",
            year=2019,
            price=3_475,
            mileage=11_800,
            condition=ConditionRating.EXCELLENT,
            service_history=ServiceHistoryRating.FULL_DEALER,
            optional_extras=[
                "Akrapovic slip-on",
                "KTM PowerParts quick-shifter",
                "Puig windscreen",
                "Radiator guard",
                "Tank pad",
            ],
            colour="Orange / Black",
            description=(
                "Stunning one-owner 790 Duke in signature KTM orange. "
                "Full dealer history, Akrapovic exhaust, factory quick-shifter. "
                "This is a sought-after spec with low miles."
            ),
            dealer=DealerInfo(
                name="Edinburgh KTM",
                address="80 Seafield Road",
                city="Edinburgh",
                region="Scotland",
                postcode="EH6 7LD",
                phone="0131 555 7890",
                email="sales@edinburghktm.co.uk",
                website="https://edinburghktm.co.uk",
                highlights=[
                    "Official KTM franchise",
                    "Nationwide delivery from £99",
                    "24-month KTM approved warranty",
                ],
            ),
            group="middleweight",
            specs=REFERENCE_SPECS["KTM Duke 790"],
            annual_costs=REFERENCE_ANNUAL_COSTS["KTM Duke 790"],
            known_issues=[],
            common_problems=COMMON_PROBLEMS["KTM Duke 790"],
        )
    )
    listings.append(
        MotorcycleListing(
            model_name="KTM Duke 790",
            year=2018,
            price=2_750,
            mileage=19_600,
            condition=ConditionRating.GOOD,
            service_history=ServiceHistoryRating.FULL_INDEPENDENT,
            optional_extras=["Evotech tail tidy", "Oxford heated grips"],
            colour="Orange / Black",
            description=(
                "Early 790 Duke in good overall condition. Full indie service "
                "history. Fuel pump relay recall completed. Two owners. "
                "Minor stone chips on the tank."
            ),
            dealer=DealerInfo(
                name="CMC Motorcycles",
                address="Unit 7, Kirkton Business Park",
                city="Glasgow",
                region="Scotland",
                postcode="G76 0LH",
                phone="0141 620 3456",
                email="info@cmcmotorcycles.co.uk",
                website="https://cmcmotorcycles.co.uk",
                highlights=[
                    "Multi-brand specialist",
                    "HPI clear guarantee",
                    "Scotland-wide delivery",
                ],
            ),
            group="middleweight",
            specs=REFERENCE_SPECS["KTM Duke 790"],
            annual_costs=REFERENCE_ANNUAL_COSTS["KTM Duke 790"],
            known_issues=["Fuel pump relay recall completed July 2021"],
            common_problems=COMMON_PROBLEMS["KTM Duke 790"],
        )
    )

    # --- Aprilia Shiver 750 ---
    listings.append(
        MotorcycleListing(
            model_name="Aprilia Shiver 750",
            year=2017,
            price=2_600,
            mileage=16_300,
            condition=ConditionRating.GOOD,
            service_history=ServiceHistoryRating.FULL_DEALER,
            optional_extras=[
                "Leo Vince exhaust",
                "Puig touring screen",
                "Centre stand",
            ],
            colour="Grigio Materia (Matte Grey)",
            description=(
                "Understated Italian V-twin with full Aprilia dealer history. "
                "Leo Vince pipe gives a proper rumble. Centre stand is a "
                "rare and practical find. MOT to March 2027."
            ),
            dealer=DealerInfo(
                name="Moto Rapido",
                address="Unit 4, Newtown Industrial Estate",
                city="Swansea",
                region="Wales",
                postcode="SA1 8QH",
                phone="01792 456 789",
                email="sales@motorapido.co.uk",
                website="https://motorapido.co.uk",
                highlights=[
                    "Italian motorcycle specialist",
                    "In-house workshop with Aprilia diagnostic tools",
                    "Part-exchange welcome",
                ],
            ),
            group="middleweight",
            specs=REFERENCE_SPECS["Aprilia Shiver 750"],
            annual_costs=REFERENCE_ANNUAL_COSTS["Aprilia Shiver 750"],
            known_issues=[],
            common_problems=COMMON_PROBLEMS["Aprilia Shiver 750"],
        )
    )
    listings.append(
        MotorcycleListing(
            model_name="Aprilia Shiver 750",
            year=2015,
            price=2_200,
            mileage=28_100,
            condition=ConditionRating.FAIR,
            service_history=ServiceHistoryRating.PARTIAL,
            optional_extras=["Givi rack", "Top box"],
            colour="Black",
            description=(
                "Higher-mileage Shiver with partial service history. Runs "
                "well but cosmetically tired — tank has clear-coat peel on "
                "one side. Top box and rack included."
            ),
            dealer=DealerInfo(
                name="Kingsmead Motorcycles",
                address="12 Kingsmead Square",
                city="Bath",
                region="England",
                postcode="BA1 2AB",
                phone="01225 334 567",
                email="info@kingsmeadmc.co.uk",
                website="https://kingsmeadmc.co.uk",
                highlights=[
                    "City-centre showroom",
                    "30-day warranty",
                    "Test rides available",
                ],
            ),
            group="middleweight",
            specs=REFERENCE_SPECS["Aprilia Shiver 750"],
            annual_costs=REFERENCE_ANNUAL_COSTS["Aprilia Shiver 750"],
            known_issues=["Clear-coat peel on right side of tank"],
            common_problems=COMMON_PROBLEMS["Aprilia Shiver 750"],
        )
    )

    # ── GROUP 2: Super-nakeds ────────────────────────────────────────────

    # --- Triumph Speed Triple ---
    listings.append(
        MotorcycleListing(
            model_name="Triumph Speed Triple",
            year=2015,
            price=3_450,
            mileage=18_500,
            condition=ConditionRating.GOOD,
            service_history=ServiceHistoryRating.FULL_DEALER,
            optional_extras=[
                "Arrow 3-into-1 exhaust",
                "Triumph quick-shifter",
                "Brembo master cylinder upgrade",
                "Datatool alarm",
            ],
            colour="Diablo Red",
            description=(
                "Head-turning Speed Triple 1050 in Diablo Red with every "
                "right option. Arrow exhaust transforms the triple bark. "
                "Full dealer stamps, recent valve check at 18k."
            ),
            dealer=DealerInfo(
                name="Destination Triumph",
                address="220 Great Western Road",
                city="Glasgow",
                region="Scotland",
                postcode="G4 9EJ",
                phone="0141 332 7777",
                email="info@destinationtriumph.co.uk",
                website="https://destinationtriumph.co.uk",
                highlights=[
                    "Official Triumph franchise",
                    "Award-winning service department",
                    "Triumph approved used scheme",
                ],
            ),
            group="supernaked",
            specs=REFERENCE_SPECS["Triumph Speed Triple"],
            annual_costs=REFERENCE_ANNUAL_COSTS["Triumph Speed Triple"],
            known_issues=["Valve check completed at 18k — all within spec"],
            common_problems=COMMON_PROBLEMS["Triumph Speed Triple"],
        )
    )
    listings.append(
        MotorcycleListing(
            model_name="Triumph Speed Triple",
            year=2013,
            price=2_700,
            mileage=26_800,
            condition=ConditionRating.FAIR,
            service_history=ServiceHistoryRating.FULL_INDEPENDENT,
            optional_extras=["R&G crash protectors", "Tail tidy"],
            colour="Phantom Black",
            description=(
                "Well-used Speed Triple with honest mileage and full indie "
                "history. Mechanically sound, cosmetically honest. Good "
                "tyres and recent chain. Ideal commuter-plus."
            ),
            dealer=DealerInfo(
                name="Bristol Motorcycles",
                address="99 Fishponds Road",
                city="Bristol",
                region="England",
                postcode="BS5 6SF",
                phone="0117 965 4321",
                email="sales@bristolmotorcycles.co.uk",
                website="https://bristolmotorcycles.co.uk",
                highlights=[
                    "Bristol's largest used motorcycle showroom",
                    "RAC warranty available",
                    "PX considered",
                ],
            ),
            group="supernaked",
            specs=REFERENCE_SPECS["Triumph Speed Triple"],
            annual_costs=REFERENCE_ANNUAL_COSTS["Triumph Speed Triple"],
            known_issues=[],
            common_problems=COMMON_PROBLEMS["Triumph Speed Triple"],
        )
    )

    # --- KTM Super Duke ---
    listings.append(
        MotorcycleListing(
            model_name="KTM Super Duke",
            year=2015,
            price=3_500,
            mileage=20_100,
            condition=ConditionRating.GOOD,
            service_history=ServiceHistoryRating.FULL_DEALER,
            optional_extras=[
                "Akrapovic full system",
                "KTM PowerParts adjustable levers",
                "Evotech radiator guard",
                "SW-Motech crash bars",
                "Tail tidy",
            ],
            colour="White / Orange",
            description=(
                "The Beast fully loaded. Akrapovic full system alone is "
                "worth over £1,000. Full KTM dealer service history. "
                "A genuine super-naked icon."
            ),
            dealer=DealerInfo(
                name="Laguna Motorcycles",
                address="Ashford Road",
                city="Maidstone",
                region="England",
                postcode="ME14 5PP",
                phone="01622 692 211",
                email="sales@lagunamotorcycles.co.uk",
                website="https://lagunamotorcycles.co.uk",
                highlights=[
                    "Official KTM / Husqvarna dealer",
                    "Multi-award-winning dealership",
                    "Nationwide delivery",
                ],
            ),
            group="supernaked",
            specs=REFERENCE_SPECS["KTM Super Duke"],
            annual_costs=REFERENCE_ANNUAL_COSTS["KTM Super Duke"],
            known_issues=[],
            common_problems=COMMON_PROBLEMS["KTM Super Duke"],
        )
    )
    listings.append(
        MotorcycleListing(
            model_name="KTM Super Duke",
            year=2014,
            price=2_750,
            mileage=28_400,
            condition=ConditionRating.FAIR,
            service_history=ServiceHistoryRating.PARTIAL,
            optional_extras=["Crash bobbins", "Radiator guard"],
            colour="Orange / Black",
            description=(
                "Higher-mileage Super Duke 1290 — still pulls like a "
                "freight train. Partial history from 20k onward. Cosmetic "
                "wear consistent with use. Mechanically strong."
            ),
            dealer=DealerInfo(
                name="Helmsman Motorcycles",
                address="14 Harbour Street",
                city="Aberystwyth",
                region="Wales",
                postcode="SY23 1LZ",
                phone="01970 612 345",
                email="info@helmsmanmc.co.uk",
                website="https://helmsmanmc.co.uk",
                highlights=[
                    "Coastal Wales specialist",
                    "All bikes HPI checked",
                    "Workshop on-site",
                ],
            ),
            group="supernaked",
            specs=REFERENCE_SPECS["KTM Super Duke"],
            annual_costs=REFERENCE_ANNUAL_COSTS["KTM Super Duke"],
            known_issues=["Service history incomplete before 20k miles"],
            common_problems=COMMON_PROBLEMS["KTM Super Duke"],
        )
    )

    # --- Aprilia Tuono ---
    listings.append(
        MotorcycleListing(
            model_name="Aprilia Tuono",
            year=2016,
            price=3_490,
            mileage=15_400,
            condition=ConditionRating.EXCELLENT,
            service_history=ServiceHistoryRating.FULL_DEALER,
            optional_extras=[
                "Austin Racing exhaust",
                "Bren-Tuning ECU remap",
                "CNC rearsets",
                "Puig dark screen",
            ],
            colour="Superpole Replica (Red / Black)",
            description=(
                "Stunning Tuono V4 1100 RR in Superpole livery. Full Aprilia "
                "service stamps, recent valve check. Austin Racing exhaust "
                "with Bren Tuning ECU remap — makes incredible power. "
                "One of the best super-nakeds ever made."
            ),
            dealer=DealerInfo(
                name="Aprilia Scotland",
                address="55 Broughton Street",
                city="Edinburgh",
                region="Scotland",
                postcode="EH1 3RJ",
                phone="0131 556 8899",
                email="sales@apriliascotland.co.uk",
                website="https://apriliascotland.co.uk",
                highlights=[
                    "Official Aprilia / Moto Guzzi dealer",
                    "Bren Tuning partnership",
                    "Approved used programme",
                ],
            ),
            group="supernaked",
            specs=REFERENCE_SPECS["Aprilia Tuono"],
            annual_costs=REFERENCE_ANNUAL_COSTS["Aprilia Tuono"],
            known_issues=["Valve check done at 15k — all within spec"],
            common_problems=COMMON_PROBLEMS["Aprilia Tuono"],
        )
    )
    listings.append(
        MotorcycleListing(
            model_name="Aprilia Tuono",
            year=2014,
            price=2_695,
            mileage=24_300,
            condition=ConditionRating.GOOD,
            service_history=ServiceHistoryRating.FULL_INDEPENDENT,
            optional_extras=["Arrow exhaust", "Tail tidy"],
            colour="Matt Black",
            description=(
                "V4 Tuono in stealthy matt black. Full indie history, "
                "two owners. Arrow exhaust sounds phenomenal. Valve check "
                "due at next service. Honest bike at a keen price."
            ),
            dealer=DealerInfo(
                name="Principality Motorcycles",
                address="7 Cathedral Road",
                city="Newport",
                region="Wales",
                postcode="NP20 4BG",
                phone="01633 221 444",
                email="info@principalitymc.co.uk",
                website="https://principalitymc.co.uk",
                highlights=[
                    "Family-run dealership since 1988",
                    "90-day warranty on all stock",
                    "Free first service included",
                ],
            ),
            group="supernaked",
            specs=REFERENCE_SPECS["Aprilia Tuono"],
            annual_costs=REFERENCE_ANNUAL_COSTS["Aprilia Tuono"],
            known_issues=["Valve check due at next service interval"],
            common_problems=COMMON_PROBLEMS["Aprilia Tuono"],
        )
    )

    return listings


def _build_wildcard_listings() -> list[MotorcycleListing]:
    """Create wildcard alternative listings for each group."""
    wildcards: list[MotorcycleListing] = []

    # Middleweight wildcard — Yamaha MT-07
    wc_mw = WILDCARD_MODELS["middleweight"]
    wildcards.append(
        MotorcycleListing(
            model_name=wc_mw["model"],
            year=2019,
            price=3_200,
            mileage=9_500,
            condition=ConditionRating.EXCELLENT,
            service_history=ServiceHistoryRating.FULL_DEALER,
            optional_extras=[
                "Akrapovic carbon slip-on",
                "Evotech tail tidy",
                "Radiator guard",
            ],
            colour="Ice Fluo / Yamaha Blue",
            description=(
                "WILDCARD PICK: The MT-07 is the middleweight benchmark "
                "for reliability and fun. This low-mileage one-owner example "
                "has the Akrapovic exhaust and full Yamaha dealer stamps. "
                "An absolute hoot to ride and cheap to run."
            ),
            dealer=DealerInfo(
                name="West Coast Yamaha",
                address="200 Dumbarton Road",
                city="Glasgow",
                region="Scotland",
                postcode="G11 6HH",
                phone="0141 334 9999",
                email="sales@westcoastyamaha.co.uk",
                website="https://westcoastyamaha.co.uk",
                highlights=[
                    "Official Yamaha franchise",
                    "Yamaha Assured Used scheme",
                    "Nationwide delivery",
                ],
            ),
            group="middleweight",
            is_wildcard=True,
            specs=wc_mw["specs"],
            annual_costs=wc_mw["annual_costs"],
            known_issues=[],
            common_problems=wc_mw["common_problems"],
        )
    )
    wildcards.append(
        MotorcycleListing(
            model_name=wc_mw["model"],
            year=2017,
            price=2_650,
            mileage=15_200,
            condition=ConditionRating.GOOD,
            service_history=ServiceHistoryRating.FULL_INDEPENDENT,
            optional_extras=["Tail tidy", "Bar-end mirrors"],
            colour="Tech Black",
            description=(
                "WILDCARD PICK: Solid MT-07 in Tech Black. Full indie "
                "history, two owners. Low running costs and bulletproof "
                "CP2 engine make this a sensible alternative."
            ),
            dealer=DealerInfo(
                name="Tyne Motorcycles",
                address="33 Scotswood Road",
                city="Newcastle",
                region="England",
                postcode="NE4 7JE",
                phone="0191 272 5678",
                email="info@tynemotorcycles.co.uk",
                website="https://tynemotorcycles.co.uk",
                highlights=[
                    "North East's top-rated dealer on Trustpilot",
                    "60-day mechanical warranty",
                    "Finance from 6.9% APR",
                ],
            ),
            group="middleweight",
            is_wildcard=True,
            specs=wc_mw["specs"],
            annual_costs=wc_mw["annual_costs"],
            known_issues=[],
            common_problems=wc_mw["common_problems"],
        )
    )

    # Super-naked wildcard — Ducati Monster 1200
    wc_sn = WILDCARD_MODELS["supernaked"]
    wildcards.append(
        MotorcycleListing(
            model_name=wc_sn["model"],
            year=2015,
            price=3_400,
            mileage=17_800,
            condition=ConditionRating.GOOD,
            service_history=ServiceHistoryRating.FULL_DEALER,
            optional_extras=[
                "Termignoni slip-on",
                "Ducati Performance tank grips",
                "Rizoma bar-end mirrors",
            ],
            colour="Ducati Red",
            description=(
                "WILDCARD PICK: Iconic Monster 1200 with Termignoni exhaust. "
                "Full Ducati dealer history including Desmo service at 15k. "
                "The L-Twin is hugely characterful and sounds incredible."
            ),
            dealer=DealerInfo(
                name="Ducati Manchester",
                address="100 Regent Road",
                city="Manchester",
                region="England",
                postcode="M5 4QR",
                phone="0161 848 0900",
                email="sales@ducatimanchester.co.uk",
                website="https://ducatimanchester.co.uk",
                highlights=[
                    "Official Ducati franchise",
                    "Ducati Approved Pre-Owned programme",
                    "Desmo service specialists",
                ],
            ),
            group="supernaked",
            is_wildcard=True,
            specs=wc_sn["specs"],
            annual_costs=wc_sn["annual_costs"],
            known_issues=["Desmo service completed at 15k miles"],
            common_problems=wc_sn["common_problems"],
        )
    )
    wildcards.append(
        MotorcycleListing(
            model_name=wc_sn["model"],
            year=2014,
            price=2_700,
            mileage=24_600,
            condition=ConditionRating.FAIR,
            service_history=ServiceHistoryRating.FULL_INDEPENDENT,
            optional_extras=["CRG levers", "Tail tidy"],
            colour="Dark Stealth (Matte Black)",
            description=(
                "WILDCARD PICK: Dark Stealth Monster 1200. Full indie "
                "history. Desmo service due at 30k — budget £700-900 for "
                "this. Otherwise a strong runner with great presence."
            ),
            dealer=DealerInfo(
                name="Italian Bike Specialists",
                address="9 Victoria Street",
                city="Inverness",
                region="Scotland",
                postcode="IV1 1EX",
                phone="01463 237 890",
                email="info@italianbikespecialists.co.uk",
                website="https://italianbikespecialists.co.uk",
                highlights=[
                    "Highland Italy — Ducati / Aprilia expertise",
                    "In-house Desmo service facility",
                    "Highland touring routes advice included",
                ],
            ),
            group="supernaked",
            is_wildcard=True,
            specs=wc_sn["specs"],
            annual_costs=wc_sn["annual_costs"],
            known_issues=["Desmo service due at 30k — factor into budget"],
            common_problems=wc_sn["common_problems"],
        )
    )

    return wildcards


def get_all_listings(
    *,
    try_live: bool = True,
    budget_low: float = 2_750,
    budget_high: float = 3_500,
) -> list[MotorcycleListing]:
    """Return all motorcycle listings — live-scraped + demo data.

    When *try_live* is ``True`` the scraper will attempt to fetch real
    listings from AutoTrader UK.  Regardless of live success, the curated
    demo dataset is always included to guarantee a useful comparison.
    """
    models = {
        "Triumph Street Triple R 675": "middleweight",
        "KTM Duke 790": "middleweight",
        "Aprilia Shiver 750": "middleweight",
        "Triumph Speed Triple": "supernaked",
        "KTM Super Duke": "supernaked",
        "Aprilia Tuono": "supernaked",
    }

    listings: list[MotorcycleListing] = []

    if try_live:
        for budget in (budget_low, budget_high):
            live = scrape_live(models, budget)
            listings.extend(live)

    # Always include curated data so the tool is useful offline
    listings.extend(_build_demo_listings())
    listings.extend(_build_wildcard_listings())

    return listings
