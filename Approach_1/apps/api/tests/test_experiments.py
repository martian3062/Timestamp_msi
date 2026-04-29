import pytest

from app.models.experiments import ExperimentGridRequest
from app.services.experiments import ExperimentService
from app.services.vm import VmService


def test_experiment_plan_expands_grid_with_stable_ids() -> None:
    service = ExperimentService()
    plan = service.build_plan(
        ExperimentGridRequest(
            feature_extractors=["resnet50_imagenet"],
            mil_models=["attention_mil", "transmil"],
            learning_rates=[1e-4],
            epochs=[5, 10],
            seeds=[310],
            folds=[1, 2],
        )
    )

    assert plan.trial_count == 4
    assert plan.trials[0].trial_id.startswith("trial_")
    assert plan.trials[0].folds == [1, 2]
    assert {trial.mil_model for trial in plan.trials} == {"attention_mil", "transmil"}
    assert {trial.epochs for trial in plan.trials} == {5, 10}


def test_experiment_plan_respects_max_trials() -> None:
    service = ExperimentService()
    plan = service.build_plan(
        ExperimentGridRequest(
            feature_extractors=["a", "b"],
            mil_models=["m1", "m2"],
            learning_rates=[1e-4, 1e-5],
            epochs=[1, 2],
            seeds=[1],
            max_trials=3,
        )
    )

    assert plan.trial_count == 3


def test_vm_project_path_rejects_unsafe_relative_paths() -> None:
    service = VmService()

    with pytest.raises(ValueError):
        service.project_path("../secrets.txt")

    with pytest.raises(ValueError):
        service.project_path("/tmp/secrets.txt")
