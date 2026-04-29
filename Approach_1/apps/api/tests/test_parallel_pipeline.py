from app.api.routes.parallel_pipeline import build_parallel_metrics


def test_parallel_metrics_are_built_from_completed_records() -> None:
    rows = build_parallel_metrics(
        {
            "Approach1": [
                {
                    "metrics": {
                        "mean_auroc": 0.81,
                        "mean_auprc": 0.72,
                        "balanced_accuracy": 0.76,
                    }
                }
            ],
            "Approach2": [
                {
                    "metrics": {
                        "auroc": 0.86,
                        "auprc": 0.80,
                        "f1_score": 0.77,
                    }
                }
            ],
            "MonteCarlo": [
                {
                    "metrics": {
                        "stability_score": 0.83,
                        "mean_auroc": 0.84,
                        "msi_h_sensitivity": 0.79,
                    }
                }
            ],
        }
    )

    by_name = {row.name: row for row in rows}

    assert by_name["AUROC"].Approach1 == 0.81
    assert by_name["AUROC"].Approach2 == 0.86
    assert by_name["AUROC"].MonteCarlo == 0.84
    assert by_name["Stable Score"].MonteCarlo == 0.83
    assert by_name["F1 Score"].Approach2 == 0.77


def test_parallel_metrics_do_not_emit_rows_without_artifacts() -> None:
    rows = build_parallel_metrics(
        {
            "Approach1": [],
            "Approach2": [],
            "MonteCarlo": [],
        }
    )

    assert rows == []
