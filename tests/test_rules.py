"""Unit tests for the shared policy rules.

Every expected number here was calculated by hand from references/policy.md
before the code was written. If a test fails, the code drifted from policy.
"""

import pytest

import donor_rules as rules


class TestParseGifts:
    def test_parses_pipe_separated_pairs(self):
        assert rules.parse_gifts("2019:500|2021:1200") == [(2019, 500.0), (2021, 1200.0)]

    def test_accepts_dollar_signs_and_commas(self):
        assert rules.parse_gifts("2020:$1,500") == [(2020, 1500.0)]

    def test_rejects_empty(self):
        with pytest.raises(ValueError):
            rules.parse_gifts("")

    def test_rejects_garbage_with_specific_message(self):
        with pytest.raises(ValueError, match="unparseable gift entry"):
            rules.parse_gifts("2019:500|banana")

    def test_rejects_zero_and_negative_amounts(self):
        with pytest.raises(ValueError, match="non-positive"):
            rules.parse_gifts("2019:0")


class TestTierAndStatus:
    @pytest.mark.parametrize("lifetime,expected", [
        (50_000, "Platinum"),
        (49_999, "Gold"),
        (10_000, "Gold"),
        (9_999, "Silver"),
        (1_000, "Silver"),
        (999, "Bronze"),
        (0, "Bronze"),
    ])
    def test_tier_boundaries(self, lifetime, expected):
        assert rules.compute_tier(lifetime) == expected

    def test_lapsed_is_strictly_more_than_three_years(self):
        assert rules.is_lapsed(2020, 2024) is True      # 4 years: lapsed
        assert rules.is_lapsed(2021, 2024) is False     # exactly 3: not lapsed

    def test_planted_fixture_traps(self):
        # These donors are mislabeled in the original skill's embedded table.
        assert rules.compute_tier(25_000) == "Gold"     # Ruth Andersen, filed Silver
        assert rules.compute_tier(17_000) == "Gold"     # Ada Yamamoto-Pierce, filed Silver
        assert rules.compute_tier(22_000) == "Gold"     # Shirley Magnusdottir, filed Silver
        assert rules.compute_tier(2_600) == "Silver"    # Arthur Mwangi, filed Bronze


class TestRounding:
    def test_half_rounds_up_not_to_even(self):
        assert rules.round_half_up(375) == 400
        assert rules.round_half_up(325) == 350

    def test_rounds_down_below_half(self):
        assert rules.round_half_up(374) == 350

    def test_rounds_up_above_half(self):
        assert rules.round_half_up(376) == 400


class TestComputeAsk:
    def test_platinum_emergency_with_volunteer(self):
        # Earl Fontaine: 40% of 90000 = 36000, +100 volunteer, x1.2 emergency
        # = 43320, rounded to 43300.
        result = rules.compute_ask(
            tier="Platinum", lapsed=False, largest_gift=90_000,
            last_gift_year=2022, volunteer=True,
            campaign_type="emergency_appeal", as_of_year=2024,
        )
        assert result.amount == 43_300

    def test_loyalty_applies_only_to_prior_full_year(self):
        # Ralph Osei-Bonsu gave in 2023 (as_of 2024): loyalty applies.
        # 32000 x 1.1 = 35200, +100 = 35300, x1.2 = 42360 -> 42350.
        result = rules.compute_ask(
            tier="Platinum", lapsed=False, largest_gift=80_000,
            last_gift_year=2023, volunteer=True,
            campaign_type="emergency_appeal", as_of_year=2024,
        )
        assert result.amount == 42_350

        # A gift in the as_of year itself is not "last year".
        result = rules.compute_ask(
            tier="Silver", lapsed=False, largest_gift=1_500,
            last_gift_year=2024, volunteer=True,
            campaign_type="emergency_appeal", as_of_year=2024,
        )
        assert result.amount == 400  # 225 + 100 = 325, x1.2 = 390 -> 400

    def test_rounding_happens_once_at_the_end(self):
        # Dorothy Callahan: 875 x 1.1 = 962.5, x1.2 = 1155 -> 1150.
        # Rounding mid-formula (as the original skill implied) would give
        # a different, path-dependent number.
        result = rules.compute_ask(
            tier="Gold", lapsed=False, largest_gift=3_500,
            last_gift_year=2023, volunteer=False,
            campaign_type="emergency_appeal", as_of_year=2024,
        )
        assert result.amount == 1_150

    def test_lapsed_small_donor_gets_flat_reengagement_ask(self):
        result = rules.compute_ask(
            tier="Silver", lapsed=True, largest_gift=700,
            last_gift_year=2019, volunteer=False,
            campaign_type="emergency_appeal", as_of_year=2024,
        )
        assert result.amount == 50

    def test_lapsed_major_donor_gets_no_automated_letter(self):
        result = rules.compute_ask(
            tier="Platinum", lapsed=True, largest_gift=50_000,
            last_gift_year=2020, volunteer=False,
            campaign_type="emergency_appeal", as_of_year=2024,
        )
        assert result.amount is None
        assert result.review_reasons

    def test_minimum_ask_floor(self):
        result = rules.compute_ask(
            tier="Silver", lapsed=True, largest_gift=100,
            last_gift_year=2019, volunteer=False,
            campaign_type="annual_fund", as_of_year=2024,
        )
        assert result.amount == 50

    def test_ask_exceeding_largest_gift_warns(self):
        result = rules.compute_ask(
            tier="Silver", lapsed=False, largest_gift=120,
            last_gift_year=2023, volunteer=True,
            campaign_type="emergency_appeal", as_of_year=2024,
        )
        # 18 x 1.1 = 19.8, +100 = 119.8, x1.2 = 143.76 -> 150 > 120
        assert result.amount == 150
        assert result.warnings

    def test_every_ask_has_an_audit_trace(self):
        result = rules.compute_ask(
            tier="Gold", lapsed=False, largest_gift=10_000,
            last_gift_year=2023, volunteer=True,
            campaign_type="annual_fund", as_of_year=2024,
        )
        assert len(result.trace) >= 3


class TestConfidenceBands:
    """The fail, report, pass rubric: below 0.70 blocked, below 0.90 held."""

    @pytest.mark.parametrize("confidence,band", [
        (0.69, "fail"),
        (0.70, "report"),
        (0.89, "report"),
        (0.90, "pass"),
        (1.00, "pass"),
    ])
    def test_band_boundaries(self, confidence, band):
        assert rules.confidence_band(confidence) == band

    def test_report_band_mandates_review(self):
        assert rules.review_level("Silver", 0.85, []) == "mandatory"


class TestCsvSafety:
    """Spreadsheet formula injection is neutralized in every CSV we write."""

    @pytest.mark.parametrize("hostile", [
        '=HYPERLINK("http://evil.example","click")',
        "+1+1",
        "-2+3",
        "@SUM(A1)",
    ])
    def test_formula_prefixes_are_neutralized(self, hostile):
        assert rules.csv_safe(hostile) == "'" + hostile

    def test_ordinary_values_pass_through(self):
        assert rules.csv_safe("Ruth Andersen") == "Ruth Andersen"
        assert rules.csv_safe("2019:500|2021:1200") == "2019:500|2021:1200"
        assert rules.csv_safe(43300) == "43300"


class TestLetterSchema:
    SCHEMA = {
        "required": ["donor_id", "salutation", "ask_paragraph", "donation_url"],
        "properties": {
            "donor_id": {}, "salutation": {}, "ask_paragraph": {},
            "donation_url": {}, "ps_line": {},
        },
        "constraints": {"ask_paragraph_dollar_amounts": 1},
    }

    def valid_model(self):
        return {
            "donor_id": "test-donor",
            "salutation": "Dear Test Donor,",
            "ask_paragraph": "Please consider a gift of $500.",
            "donation_url": "https://example.org/donate",
            "ps_line": "",
        }

    def test_valid_model_passes(self):
        assert rules.validate_letter_model(self.valid_model(), self.SCHEMA) == []

    def test_missing_required_field_fails(self):
        model = self.valid_model()
        model["salutation"] = ""
        errors = rules.validate_letter_model(model, self.SCHEMA)
        assert any("salutation" in error for error in errors)

    def test_two_dollar_amounts_fail(self):
        model = self.valid_model()
        model["ask_paragraph"] = "Give $500 or even $1,000."
        errors = rules.validate_letter_model(model, self.SCHEMA)
        assert any("dollar" in error for error in errors)

    def test_unknown_field_fails(self):
        model = self.valid_model()
        model["tracking_pixel"] = "https://evil.example/pixel"
        errors = rules.validate_letter_model(model, self.SCHEMA)
        assert any("unknown field" in error for error in errors)

    def test_non_http_url_fails(self):
        model = self.valid_model()
        model["donation_url"] = "javascript:alert(1)"
        errors = rules.validate_letter_model(model, self.SCHEMA)
        assert any("http" in error for error in errors)


class TestStreakAndReview:
    def test_streak_counts_back_from_prior_year(self):
        assert rules.giving_streak([2021, 2022, 2023], 2024) == 3
        assert rules.giving_streak([2021, 2023], 2024) == 1
        assert rules.giving_streak([2021, 2022], 2024) == 0

    def test_platinum_review_is_always_mandatory(self):
        assert rules.review_level("Platinum", 1.0, []) == "mandatory"

    def test_any_warning_recommends_review(self):
        assert rules.review_level("Silver", 0.9, []) == "recommended"

    def test_low_confidence_mandates_review(self):
        assert rules.review_level("Bronze", 0.6, []) == "mandatory"

    def test_clean_record_needs_no_review(self):
        assert rules.review_level("Gold", 1.0, []) == "none"


class TestNames:
    def test_split_keeps_hyphenated_family_names(self):
        assert rules.split_name("Ada Yamamoto-Pierce") == ("Ada", "Yamamoto-Pierce")

    def test_slug_is_filesystem_safe(self):
        assert rules.slugify("Ralph Osei-Bonsu") == "ralph-osei-bonsu"
