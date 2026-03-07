"""
Unit tests for domain/gig.py — pure validation helpers.
No DB, no FastAPI. All functions under test are synchronous validators.
"""

import pytest

from src.domain.gig import (
    GigValidationError,
    validate_currency_token,
    validate_milestone_count,
    validate_milestone_sum,
)


# ---------------------------------------------------------------------------
# validate_milestone_count
# ---------------------------------------------------------------------------


class TestValidateMilestoneCount:
    def test_valid_single_milestone(self) -> None:
        validate_milestone_count(1)  # should not raise

    def test_valid_max_milestones(self) -> None:
        validate_milestone_count(10)  # should not raise

    def test_zero_milestones_raises(self) -> None:
        with pytest.raises(GigValidationError) as exc_info:
            validate_milestone_count(0)
        assert exc_info.value.code == "MILESTONE_COUNT_TOO_LOW"

    def test_eleven_milestones_raises(self) -> None:
        with pytest.raises(GigValidationError) as exc_info:
            validate_milestone_count(11)
        assert exc_info.value.code == "MILESTONE_COUNT_TOO_HIGH"

    def test_negative_count_raises(self) -> None:
        with pytest.raises(GigValidationError) as exc_info:
            validate_milestone_count(-1)
        assert exc_info.value.code == "MILESTONE_COUNT_TOO_LOW"


# ---------------------------------------------------------------------------
# validate_milestone_sum
# ---------------------------------------------------------------------------


class TestValidateMilestoneSum:
    def test_matching_sum_passes(self) -> None:
        validate_milestone_sum("1000", ["400", "600"])  # should not raise

    def test_single_milestone_equal_to_total(self) -> None:
        validate_milestone_sum("500", ["500"])  # should not raise

    def test_sum_mismatch_raises(self) -> None:
        with pytest.raises(GigValidationError) as exc_info:
            validate_milestone_sum("1000", ["400", "500"])
        assert exc_info.value.code == "MILESTONE_SUM_MISMATCH"
        assert "900" in exc_info.value.message
        assert "1000" in exc_info.value.message

    def test_sum_over_total_raises(self) -> None:
        with pytest.raises(GigValidationError) as exc_info:
            validate_milestone_sum("1000", ["600", "600"])
        assert exc_info.value.code == "MILESTONE_SUM_MISMATCH"

    def test_invalid_total_amount_raises(self) -> None:
        with pytest.raises(GigValidationError) as exc_info:
            validate_milestone_sum("not_a_number", ["100"])
        assert exc_info.value.code == "INVALID_TOTAL_AMOUNT"

    def test_invalid_milestone_amount_raises(self) -> None:
        with pytest.raises(GigValidationError) as exc_info:
            validate_milestone_sum("1000", ["abc", "def"])
        assert exc_info.value.code == "INVALID_MILESTONE_AMOUNT"

    def test_empty_milestone_list_sum_zero_mismatch(self) -> None:
        with pytest.raises(GigValidationError) as exc_info:
            validate_milestone_sum("1000", [])
        assert exc_info.value.code == "MILESTONE_SUM_MISMATCH"

    def test_zero_total_with_zero_sum_passes(self) -> None:
        # Edge case: technically valid (though amount validators would block it)
        validate_milestone_sum("0", ["0"])


# ---------------------------------------------------------------------------
# validate_currency_token
# ---------------------------------------------------------------------------


class TestValidateCurrencyToken:
    def test_eth_no_token_passes(self) -> None:
        validate_currency_token("CURRENCY_ETH", "")  # should not raise

    def test_eth_with_token_passes(self) -> None:
        # token_address allowed but not required for ETH
        validate_currency_token("CURRENCY_ETH", "0xabc")  # should not raise

    def test_usdc_with_token_passes(self) -> None:
        validate_currency_token(
            "CURRENCY_USDC", "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
        )

    def test_usdc_without_token_raises(self) -> None:
        with pytest.raises(GigValidationError) as exc_info:
            validate_currency_token("CURRENCY_USDC", "")
        assert exc_info.value.code == "MISSING_TOKEN_ADDRESS"

    def test_invalid_currency_raises(self) -> None:
        with pytest.raises(GigValidationError) as exc_info:
            validate_currency_token("CURRENCY_BTC", "")
        assert exc_info.value.code == "INVALID_CURRENCY"

    def test_unspecified_currency_raises(self) -> None:
        with pytest.raises(GigValidationError) as exc_info:
            validate_currency_token("CURRENCY_UNSPECIFIED", "")
        assert exc_info.value.code == "INVALID_CURRENCY"
