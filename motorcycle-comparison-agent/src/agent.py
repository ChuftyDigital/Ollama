"""
Main orchestrator for the Motorcycle Comparison Agent.

Usage:
    python -m src.agent [--no-live] [--output PATH]

Workflow:
    1. Scrape / load motorcycle listings across UK dealer networks
    2. Score and rank each listing at two price points per group
    3. Generate a comprehensive Markdown dashboard report
    4. Write the report to disk
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from .models import MotorcycleListing
from .scoring import ScoringWeights, rank_listings
from .scraper import get_all_listings
from .report import generate_report

logger = logging.getLogger(__name__)

# Budget tiers
BUDGET_LOW = 2_750
BUDGET_HIGH = 3_500

# Groups
GROUPS = ("middleweight", "supernaked")


def _partition(
    listings: list[MotorcycleListing],
) -> dict[str, list[MotorcycleListing]]:
    """Split listings by group."""
    result: dict[str, list[MotorcycleListing]] = {g: [] for g in GROUPS}
    for lst in listings:
        if lst.group in result:
            result[lst.group].append(lst)
    return result


def _filter_by_budget(
    listings: list[MotorcycleListing],
    budget: float,
    *,
    headroom_pct: float = 0.10,
) -> list[MotorcycleListing]:
    """Return listings at or near *budget* (allowing a small overshoot)."""
    ceiling = budget * (1 + headroom_pct)
    return [l for l in listings if l.price <= ceiling]


def run(
    *,
    try_live: bool = True,
    output_path: str | Path = "output/motorcycle_comparison_dashboard.md",
    weights: ScoringWeights | None = None,
) -> Path:
    """Execute the full agent pipeline and return the report path."""
    if weights is None:
        weights = ScoringWeights()

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Gather listings
    logger.info("Gathering motorcycle listings (live=%s) ...", try_live)
    all_listings = get_all_listings(
        try_live=try_live,
        budget_low=BUDGET_LOW,
        budget_high=BUDGET_HIGH,
    )
    logger.info("Total listings collected: %d", len(all_listings))

    # 2. Partition by group
    by_group = _partition(all_listings)

    # 3. Score & rank at each budget tier
    ranked_groups: dict[str, dict[str, list[MotorcycleListing]]] = {}

    for group_name, group_listings in by_group.items():
        ranked_groups[group_name] = {}
        for budget in (BUDGET_LOW, BUDGET_HIGH):
            pool = _filter_by_budget(group_listings, budget)
            ranked = rank_listings(pool, budget, weights)
            ranked_groups[group_name][str(budget)] = ranked
            if ranked:
                best = ranked[0]
                logger.info(
                    "  [%s @ \u00a3%d] #1: %s (%d) — score %.2f",
                    group_name,
                    budget,
                    best.model_name,
                    best.year,
                    best.score,
                )

    # 4. Generate report
    logger.info("Generating Markdown dashboard ...")
    report_md = generate_report(ranked_groups, weights)
    output_path.write_text(report_md, encoding="utf-8")
    logger.info("Report written to %s", output_path)

    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Motorcycle Comparison Agent — UK dealer network analysis"
    )
    parser.add_argument(
        "--no-live",
        action="store_true",
        help="Skip live web scraping; use curated demo data only",
    )
    parser.add_argument(
        "--output",
        default="output/motorcycle_comparison_dashboard.md",
        help="Output path for the Markdown report (default: output/...)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    report_path = run(
        try_live=not args.no_live,
        output_path=args.output,
    )
    print(f"\nDashboard generated: {report_path}")
    print(f"Open the .md file in any Markdown viewer to see the full report.")


if __name__ == "__main__":
    main()
