"""
Markdown dashboard report generator.

Produces a comprehensive .md report with:
 - Executive summary dashboard
 - ASCII bar-chart visualisations
 - Per-group rankings at each price point
 - Detailed motorcycle cards (specs, dealer, costs, issues)
 - Wildcard alternatives
 - Common-problems reference
 - Running costs comparison
"""

from __future__ import annotations

import datetime
from textwrap import dedent

from .models import (
    AnnualCosts,
    COMMON_PROBLEMS,
    MotorcycleListing,
    REFERENCE_ANNUAL_COSTS,
    WILDCARD_MODELS,
)
from .scoring import ScoringWeights


# ── ASCII chart helpers ──────────────────────────────────────────────────────

_BAR_CHAR = "\u2588"  # Full block
_BAR_MAX_WIDTH = 30


def _bar(value: float, max_value: float = 10.0) -> str:
    width = int((value / max_value) * _BAR_MAX_WIDTH)
    return _BAR_CHAR * max(1, width)


def _score_bar_chart(listings: list[MotorcycleListing], title: str) -> str:
    """Produce an ASCII horizontal bar chart of overall scores."""
    lines = [f"### {title}", "", "```"]
    max_score = max((l.score for l in listings), default=1)
    for lst in listings:
        label = f"{lst.model_name} ({lst.year})"
        bar = _bar(lst.score, max_score)
        wc = " [WC]" if lst.is_wildcard else ""
        lines.append(f"  {label:<38} {bar} {lst.score:.2f}{wc}")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def _breakdown_chart(listing: MotorcycleListing) -> str:
    """Per-criterion breakdown bar chart for one listing."""
    lines = ["```"]
    for criterion, raw_score in listing.score_breakdown.items():
        label = criterion.replace("_", " ").title()
        bar = _bar(raw_score)
        lines.append(f"  {label:<20} {bar} {raw_score:.1f}/10")
    lines.append(f"  {'TOTAL':<20} {'':>30} {listing.score:.2f}")
    lines.append("```")
    return "\n".join(lines)


# ── Cost comparison table ────────────────────────────────────────────────────

def _costs_table(models: list[str]) -> str:
    """Markdown table comparing annual running costs."""
    header = "| Category |"
    sep = "|---|"
    for m in models:
        short = m.split()[-1] if len(m.split()) > 2 else m
        header += f" {short} |"
        sep += "---:|"

    rows: list[str] = [header, sep]
    categories = [
        ("Servicing", "servicing"),
        ("Insurance (est.)", "insurance_estimate"),
        ("Fuel", "fuel"),
        ("Tyres", "tyres"),
        ("Consumables", "consumables"),
        ("MOT", "mot"),
    ]

    all_costs = {m: REFERENCE_ANNUAL_COSTS.get(m) for m in models}
    # Include wildcard costs
    for group_data in WILDCARD_MODELS.values():
        name = group_data["model"]
        if name in models:
            all_costs[name] = group_data["annual_costs"]

    for cat_name, attr in categories:
        row = f"| {cat_name} |"
        for m in models:
            c = all_costs.get(m)
            val = getattr(c, attr, 0) if c else 0
            row += f" \u00a3{val:,.0f} |"
        rows.append(row)

    # Total row
    row = "| **TOTAL** |"
    for m in models:
        c = all_costs.get(m)
        total = c.total if c else 0
        row += f" **\u00a3{total:,.0f}** |"
    rows.append(row)

    return "\n".join(rows)


# ── Listing detail card ──────────────────────────────────────────────────────

def _listing_card(listing: MotorcycleListing, rank: int) -> str:
    """Full detail card for one listing."""
    wc_badge = " \U0001f0cf WILDCARD" if listing.is_wildcard else ""
    lines = [
        f"#### #{rank} — {listing.model_name} ({listing.year}){wc_badge}",
        "",
        f"**Price:** \u00a3{listing.price:,.0f} | "
        f"**Mileage:** {listing.mileage:,} miles | "
        f"**Colour:** {listing.colour}",
        f"**Condition:** {listing.condition.name.replace('_', ' ').title()} | "
        f"**Service History:** {listing.service_history.name.replace('_', ' ').title()}",
        "",
    ]

    if listing.description:
        lines.append(f"> {listing.description}")
        lines.append("")

    # Score breakdown
    lines.append(f"**Overall Score: {listing.score:.2f} / 10**")
    lines.append("")
    lines.append(_breakdown_chart(listing))
    lines.append("")

    # Specs
    if listing.specs:
        s = listing.specs
        lines.append("**Specifications:**")
        lines.append("")
        lines.append(f"| Spec | Value |")
        lines.append(f"|---|---|")
        lines.append(f"| Engine | {s.engine_cc}cc {s.engine_type} |")
        lines.append(f"| Power | {s.power_bhp} bhp |")
        lines.append(f"| Torque | {s.torque_nm} Nm |")
        lines.append(f"| Weight | {s.weight_kg} kg |")
        lines.append(f"| Seat Height | {s.seat_height_mm} mm |")
        lines.append(f"| Fuel Capacity | {s.fuel_capacity_litres} L |")
        lines.append(f"| Top Speed | {s.top_speed_mph} mph |")
        lines.append(f"| 0-60 | {s.zero_to_sixty_secs}s |")
        lines.append("")

    # Optional extras
    if listing.optional_extras:
        lines.append("**Optional Extras:**")
        for extra in listing.optional_extras:
            lines.append(f"- {extra}")
        lines.append("")

    # Known issues
    if listing.known_issues:
        lines.append("**Known Issues (this bike):**")
        for issue in listing.known_issues:
            lines.append(f"- \u26a0\ufe0f {issue}")
        lines.append("")

    # Dealer info
    if listing.dealer:
        d = listing.dealer
        lines.append("**Dealer Information:**")
        lines.append("")
        lines.append(f"| | |")
        lines.append(f"|---|---|")
        lines.append(f"| Name | **{d.name}** |")
        lines.append(f"| Address | {d.full_address} |")
        lines.append(f"| Region | {d.region} |")
        lines.append(f"| Phone | {d.phone} |")
        lines.append(f"| Email | {d.email} |")
        if d.website:
            lines.append(f"| Website | {d.website} |")
        lines.append("")
        if d.highlights:
            lines.append("**Dealer Highlights:**")
            for h in d.highlights:
                lines.append(f"- {h}")
            lines.append("")

    lines.append("---")
    lines.append("")
    return "\n".join(lines)


# ── Common problems section ──────────────────────────────────────────────────

def _common_problems_section(models: list[str]) -> str:
    """Buyer-beware problems reference for each model."""
    lines = ["## Common Problems Reference", ""]
    all_problems: dict[str, list[str]] = dict(COMMON_PROBLEMS)
    for group_data in WILDCARD_MODELS.values():
        name = group_data["model"]
        if name in models:
            all_problems[name] = group_data["common_problems"]

    for model in models:
        problems = all_problems.get(model, [])
        if not problems:
            continue
        lines.append(f"### {model}")
        lines.append("")
        for p in problems:
            lines.append(f"- {p}")
        lines.append("")

    return "\n".join(lines)


# ── Main report generator ───────────────────────────────────────────────────

def generate_report(
    ranked_groups: dict[str, dict[str, list[MotorcycleListing]]],
    weights: ScoringWeights,
) -> str:
    """Generate the full Markdown dashboard report.

    *ranked_groups* has the structure::

        {
            "middleweight": {
                "2750": [scored_listings...],
                "3500": [scored_listings...],
            },
            "supernaked": { ... },
        }
    """
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%d %B %Y, %H:%M UTC")

    # Collect all model names for cross-cutting sections
    all_model_names: list[str] = []
    for group_data in ranked_groups.values():
        for budget_listings in group_data.values():
            for lst in budget_listings:
                if lst.model_name not in all_model_names:
                    all_model_names.append(lst.model_name)

    sections: list[str] = []

    # ── Header ───────────────────────────────────────────────────────────
    sections.append(dedent(f"""\
        # Motorcycle Comparison Dashboard
        **Generated:** {now}

        ---

        ## Executive Summary

        This report compares used motorcycles across UK, Wales, and Scotland
        dealer networks at two price points (**\u00a32,750** and **\u00a33,500**),
        using a weighted scoring system to identify the best value in each
        category.

        **Scoring Weights:**

        | Criterion | Weight |
        |---|---:|
        | Price / Value | {weights.price_value:.0%} |
        | Mileage | {weights.mileage:.0%} |
        | Service History | {weights.service_history:.0%} |
        | Condition | {weights.condition:.0%} |
        | Optional Extras | {weights.optional_extras:.0%} |

        ---
    """))

    # ── Group sections ───────────────────────────────────────────────────
    group_labels = {
        "middleweight": (
            "Group 1 — Middleweights",
            "Triumph Street Triple R 675 | KTM Duke 790 | Aprilia Shiver 750",
        ),
        "supernaked": (
            "Group 2 — Super-Nakeds",
            "Triumph Speed Triple | KTM Super Duke | Aprilia Tuono",
        ),
    }

    for group_key, (group_title, group_models_str) in group_labels.items():
        group_data = ranked_groups.get(group_key, {})
        sections.append(f"## {group_title}")
        sections.append(f"*Models: {group_models_str} + Wildcard*")
        sections.append("")

        for budget_label, budget_listings in sorted(group_data.items()):
            budget_val = f"\u00a3{int(budget_label):,}"
            sections.append(f"### Budget: {budget_val}")
            sections.append("")

            if not budget_listings:
                sections.append("*No listings found at this price point.*")
                sections.append("")
                continue

            # Chart
            chart_title = f"Score Rankings — {group_title} @ {budget_val}"
            sections.append(_score_bar_chart(budget_listings, chart_title))

            # Winner callout
            winner = budget_listings[0]
            wc_note = " (Wildcard)" if winner.is_wildcard else ""
            sections.append(
                f"> **Top Pick:** {winner.model_name} ({winner.year})"
                f"{wc_note} — Score **{winner.score:.2f}**  "
            )
            sections.append(f"> {winner.description[:200]}...")
            sections.append("")

            # Detail cards
            for rank, lst in enumerate(budget_listings, start=1):
                sections.append(_listing_card(lst, rank))

        sections.append("---")
        sections.append("")

    # ── Annual Running Costs ─────────────────────────────────────────────
    sections.append("## Estimated Annual Running Costs")
    sections.append("")
    sections.append(
        "Costs are mid-range estimates for a rider aged 30+ with 5+ years "
        "NCB, based on 5,000 miles/year, garaged, and with basic "
        "comprehensive insurance."
    )
    sections.append("")
    sections.append(_costs_table(all_model_names))
    sections.append("")

    # ASCII cost comparison chart
    sections.append("### Total Annual Cost Comparison")
    sections.append("")
    sections.append("```")
    cost_data: list[tuple[str, float]] = []
    for m in all_model_names:
        c = REFERENCE_ANNUAL_COSTS.get(m)
        if c is None:
            for group_data in WILDCARD_MODELS.values():
                if group_data["model"] == m:
                    c = group_data["annual_costs"]
                    break
        if c:
            cost_data.append((m, c.total))
    cost_data.sort(key=lambda x: x[1])
    max_cost = max((c for _, c in cost_data), default=1)
    for model, total in cost_data:
        bar_w = int((total / max_cost) * _BAR_MAX_WIDTH)
        bar = _BAR_CHAR * max(1, bar_w)
        sections.append(f"  {model:<30} {bar} \u00a3{total:,.0f}/yr")
    sections.append("```")
    sections.append("")

    # ── Common Problems ──────────────────────────────────────────────────
    sections.append(_common_problems_section(all_model_names))

    # ── Methodology ──────────────────────────────────────────────────────
    sections.append(dedent("""\
        ## Methodology

        Each motorcycle is scored on five criteria, each normalised to a
        0-10 scale:

        1. **Price / Value (30%)** — How far under the target budget the
           asking price falls. Being well under budget scores higher;
           slightly over budget is penalised but not disqualifying.
        2. **Mileage (20%)** — Lower mileage relative to reasonable maximums
           for the category (45k miles for middleweights, 40k for
           super-nakeds) scores higher.
        3. **Service History (20%)** — Full dealer history scores 10/10;
           no history scores 2/10.  Independent stamps are valued but
           slightly below franchised dealer records.
        4. **Condition (20%)** — Overall physical and mechanical condition
           rated Excellent (10) to Poor (2).
        5. **Optional Extras (10%)** — Each desirable extra adds 2 points
           (capped at 10). Quality aftermarket parts (Akrapovic, Arrow,
           Brembo) are weighted equally with OEM options.

        The weighted total determines the ranking.  A **wildcard** option
        is included in each group as a potential alternative that may
        offer better value, reliability, or character outside the
        primary model set.

        ---

        *Report generated by the Motorcycle Comparison Agent.*
    """))

    return "\n\n".join(sections)
