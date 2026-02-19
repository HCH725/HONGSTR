import pytest

from scripts.report_walkforward import _latest_reason_token


@pytest.mark.parametrize(
    "failed_windows",
    [
        {
            "NEUTRAL_2023": {"reason": "NO_DATA_IN_RANGE"},
            "BULL_2024": {"reason": "NO_DATA_IN_RANGE"},
        },
        [
            {"window": "NEUTRAL_2023", "reason": "NO_DATA_IN_RANGE"},
            {"window": "BULL_2024", "reason": "NO_DATA_IN_RANGE"},
        ],
    ],
)
def test_failed_all_no_data_normalizes_to_no_data(failed_windows):
    token = _latest_reason_token(
        quick_mode=False,
        failed_windows=failed_windows,
        failure_reasons=["NO_DATA_IN_RANGE", "NO_DATA_IN_RANGE"],
        existing_token="LATEST_NOT_UPDATED_FAILED",
    )
    assert token == "LATEST_NOT_UPDATED_NO_DATA"


def test_failed_mixed_reasons_stays_failed():
    token = _latest_reason_token(
        quick_mode=False,
        failed_windows={
            "NEUTRAL_2023": {"reason": "NO_DATA_IN_RANGE"},
            "BULL_2024": {"reason": "SOME_OTHER_ERROR"},
        },
        failure_reasons=["NO_DATA_IN_RANGE", "SOME_OTHER_ERROR"],
        existing_token="LATEST_NOT_UPDATED_FAILED",
    )
    assert token == "LATEST_NOT_UPDATED_FAILED"
