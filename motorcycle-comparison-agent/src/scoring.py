"""
Weighted scoring engine for ranking motorcycle listings.

The scoring system normalises each criterion to a 0-10 scale and then applies
configurable weights.  A higher total score = a better buy.

Default weights (total = 1.0):
  - price_value       0.30   How far under budget + absolute value
  - mileage           0.20   Lower is better, normalised against group max
  - service_history   0.20   Full dealer history scores highest
  - condition         0.20   Overall physical / mechanical condition
  - optional_extras   0.10   Bonus for desirable add-ons
"""

from dataclasses import dataclass

from .models import (
    ConditionRating,
    MotorcycleListing,
    ServiceHistoryRating,
)

# Maximum reasonable mileage for used bikes in these categories
MAX_MILEAGE_MIDDLEWEIGHT = 45_000
MAX_MILEAGE_SUPERNAKED = 40_000


@dataclass
class ScoringWeights:
    price_value: float = 0.30
    mileage: float = 0.20
    service_history: float = 0.20
    condition: float = 0.20
    optional_extras: float = 0.10

    def validate(self) -> None:
        total = (
            self.price_value
            + self.mileage
            + self.service_history
            + self.condition
            + self.optional_extras
        )
        if abs(total - 1.0) > 0.001:
            raise ValueError(
                f"Scoring weights must sum to 1.0, got {total:.3f}"
            )


def _score_price(listing: MotorcycleListing, budget: float) -> float:
    """Score 0-10: 10 = well under budget, 0 = at or over budget."""
    if listing.price > budget:
        # Over-budget items get a penalty proportional to overshoot
        overshoot = (listing.price - budget) / budget
        return max(0.0, 5.0 - overshoot * 20.0)
    saving_pct = (budget - listing.price) / budget
    return min(10.0, 5.0 + saving_pct * 20.0)


def _score_mileage(listing: MotorcycleListing) -> float:
    """Score 0-10: 10 = very low mileage, 0 = at or above max."""
    max_mi = (
        MAX_MILEAGE_MIDDLEWEIGHT
        if listing.group == "middleweight"
        else MAX_MILEAGE_SUPERNAKED
    )
    if listing.mileage >= max_mi:
        return 0.0
    return 10.0 * (1.0 - listing.mileage / max_mi)


def _score_service_history(listing: MotorcycleListing) -> float:
    """Score 0-10 based on service history rating enum (1-5 mapped to 0-10)."""
    return (listing.service_history.value / 5.0) * 10.0


def _score_condition(listing: MotorcycleListing) -> float:
    """Score 0-10 based on condition rating enum (1-5 mapped to 0-10)."""
    return (listing.condition.value / 5.0) * 10.0


def _score_extras(listing: MotorcycleListing) -> float:
    """Score 0-10 based on the number of optional extras.

    Each extra adds 2 points, capped at 10.
    """
    return min(10.0, len(listing.optional_extras) * 2.0)


def score_listing(
    listing: MotorcycleListing,
    budget: float,
    weights: ScoringWeights | None = None,
) -> MotorcycleListing:
    """Compute and attach a weighted score to *listing*, returning it."""
    if weights is None:
        weights = ScoringWeights()
    weights.validate()

    breakdown: dict[str, float] = {
        "price_value": _score_price(listing, budget),
        "mileage": _score_mileage(listing),
        "service_history": _score_service_history(listing),
        "condition": _score_condition(listing),
        "optional_extras": _score_extras(listing),
    }

    weighted_total = (
        breakdown["price_value"] * weights.price_value
        + breakdown["mileage"] * weights.mileage
        + breakdown["service_history"] * weights.service_history
        + breakdown["condition"] * weights.condition
        + breakdown["optional_extras"] * weights.optional_extras
    )

    listing.score = round(weighted_total, 2)
    listing.score_breakdown = {
        k: round(v, 2) for k, v in breakdown.items()
    }
    return listing


def rank_listings(
    listings: list[MotorcycleListing],
    budget: float,
    weights: ScoringWeights | None = None,
) -> list[MotorcycleListing]:
    """Score and sort *listings* best-first for a given *budget*."""
    scored = [score_listing(l, budget, weights) for l in listings]
    scored.sort(key=lambda l: l.score, reverse=True)
    return scored
