from agentic_ai_statistics.trace_study.prediction import evaluate_prediction


def _analysis(campaign_id: str, paths: list[str]) -> dict[str, object]:
    return {
        "campaign_id": campaign_id,
        "trace_examples": [
            {"run_id": f"{campaign_id}-{index}", "state_sequence": path}
            for index, path in enumerate(paths)
        ],
    }


def test_held_out_prediction_returns_finite_model_metrics() -> None:
    training = _analysis(
        "train",
        ["START > inspect|observed > END_SUCCESS"] * 3
        + ["START > inspect|observed > END_FAILURE"],
    )
    test = _analysis(
        "test",
        ["START > inspect|observed > END_SUCCESS", "START > inspect|observed > END_FAILURE"],
    )
    result = evaluate_prediction(training, test)
    assert result["training_runs"] == 4
    assert result["test_runs"] == 2
    assert all(row["n_transitions"] == 4 for row in result["model_comparison"])
    assert all(row["mean_run_log_loss"] >= 0 for row in result["model_comparison"])
