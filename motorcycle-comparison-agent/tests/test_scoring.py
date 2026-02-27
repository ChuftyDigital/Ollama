"""Tests for the weighted scoring engine."""

import unittest

from src.models import ConditionRating, MotorcycleListing, ServiceHistoryRating
from src.scoring import ScoringWeights, rank_listings, score_listing


def _make_listing(**overrides) -> MotorcycleListing:
    defaults = dict(
        model_name="Test Bike",
        year=2018,
        price=3000,
        mileage=15000,
        condition=ConditionRating.GOOD,
        service_history=ServiceHistoryRating.FULL_DEALER,
        optional_extras=["Exhaust", "Tail tidy"],
        group="middleweight",
    )
    defaults.update(overrides)
    return MotorcycleListing(**defaults)


class TestScoringWeights(unittest.TestCase):
    def test_default_weights_are_valid(self):
        w = ScoringWeights()
        w.validate()  # should not raise

    def test_invalid_weights_raise(self):
        w = ScoringWeights(price_value=0.5)
        with self.assertRaises(ValueError):
            w.validate()


class TestScoreListing(unittest.TestCase):
    def test_under_budget_scores_higher_than_at_budget(self):
        cheap = _make_listing(price=2500)
        exact = _make_listing(price=3500)
        score_listing(cheap, budget=3500)
        score_listing(exact, budget=3500)
        self.assertGreater(
            cheap.score_breakdown["price_value"],
            exact.score_breakdown["price_value"],
        )

    def test_over_budget_penalised(self):
        over = _make_listing(price=4000)
        score_listing(over, budget=3500)
        self.assertLess(over.score_breakdown["price_value"], 5.0)

    def test_low_mileage_scores_higher(self):
        low = _make_listing(mileage=5000)
        high = _make_listing(mileage=40000)
        score_listing(low, budget=3500)
        score_listing(high, budget=3500)
        self.assertGreater(
            low.score_breakdown["mileage"],
            high.score_breakdown["mileage"],
        )

    def test_excellent_condition_beats_fair(self):
        exc = _make_listing(condition=ConditionRating.EXCELLENT)
        fair = _make_listing(condition=ConditionRating.FAIR)
        score_listing(exc, budget=3500)
        score_listing(fair, budget=3500)
        self.assertGreater(
            exc.score_breakdown["condition"],
            fair.score_breakdown["condition"],
        )

    def test_full_dealer_history_scores_max(self):
        lst = _make_listing(service_history=ServiceHistoryRating.FULL_DEALER)
        score_listing(lst, budget=3500)
        self.assertEqual(lst.score_breakdown["service_history"], 10.0)

    def test_extras_capped_at_10(self):
        many = _make_listing(
            optional_extras=["a", "b", "c", "d", "e", "f", "g"]
        )
        score_listing(many, budget=3500)
        self.assertLessEqual(many.score_breakdown["optional_extras"], 10.0)

    def test_score_is_positive(self):
        lst = _make_listing()
        score_listing(lst, budget=3500)
        self.assertGreater(lst.score, 0)


class TestRankListings(unittest.TestCase):
    def test_ranking_order(self):
        best = _make_listing(price=2500, mileage=5000,
                             condition=ConditionRating.EXCELLENT)
        mid = _make_listing(price=3000, mileage=15000,
                            condition=ConditionRating.GOOD)
        worst = _make_listing(price=3400, mileage=35000,
                              condition=ConditionRating.FAIR,
                              service_history=ServiceHistoryRating.NONE)
        ranked = rank_listings([worst, best, mid], budget=3500)
        self.assertEqual(ranked[0], best)
        self.assertEqual(ranked[-1], worst)

    def test_empty_list(self):
        self.assertEqual(rank_listings([], budget=3500), [])


if __name__ == "__main__":
    unittest.main()
