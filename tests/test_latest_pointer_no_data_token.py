from scripts.report_walkforward import _latest_reason_token


def test_no_data_token_normalized():
    token = _latest_reason_token(
        quick_mode=False,
        failed_windows=["NEUTRAL_2023", "BULL_2024"],
        failure_reasons=["No data for window", "No data ..."],
        existing_token="LATEST_NOT_UPDATED_FAILED",
    )
    assert token == "LATEST_NOT_UPDATED_NO_DATA"


def test_quick_mode_token_wins():
    token = _latest_reason_token(
        quick_mode=True,
        failed_windows=["NEUTRAL_2023"],
        failure_reasons=["No data"],
        existing_token="LATEST_NOT_UPDATED_FAILED",
    )
    assert token == "LATEST_NOT_UPDATED_QUICK_MODE"
