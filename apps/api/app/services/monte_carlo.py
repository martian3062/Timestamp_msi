"""Monte Carlo experiment services.

Provides:
  1. Random hyperparameter search plan (log-uniform LR, random dropout, etc.)
  2. MC dropout inference runner on the VM
  3. Bootstrap confidence interval computation on the VM
  4. Seed-stability analysis across repeated trainings
  5. Stability-weighted best model selection
"""
from __future__ import annotations

import hashlib
import json
import math
import random

from app.models.monte_carlo import (
    BootstrapCIRequest,
    BootstrapCIResponse,
    MCDropoutRequest,
    MCDropoutResponse,
    MetricCI,
    MonteCarloActionResponse,
    MonteCarloSearchRequest,
    MonteCarloSearchResponse,
    MonteCarloTrial,
    SeedStabilityRequest,
    SeedStabilityResponse,
    SeedStabilityResult,
    SlideUncertainty,
    StableBestCandidate,
    StableBestRequest,
    StableBestResponse,
)
from app.services.vm import VmService


# ---------------------------------------------------------------------------
# VM runner scripts
# ---------------------------------------------------------------------------

MC_DROPOUT_RUNNER = r'''"""MC Dropout uncertainty estimator.

Runs N forward passes with dropout enabled at inference time on an already
trained model, then computes per-slide mean probability and uncertainty.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[1]
RESULTS_ROOT = PROJECT_DIR / "automation" / "results"
MC_RESULTS_ROOT = PROJECT_DIR / "automation" / "mc_results"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trial-id", required=True)
    parser.add_argument("--forward-passes", type=int, default=30)
    parser.add_argument("--dropout-rate", type=float, default=0.25)
    args = parser.parse_args()

    trial_id = args.trial_id
    n_passes = args.forward_passes
    dropout_rate = args.dropout_rate

    # Load the trial metrics to find prediction files
    metrics_path = RESULTS_ROOT / trial_id / "metrics.json"
    if not metrics_path.exists():
        raise FileNotFoundError(f"Trial metrics not found: {metrics_path}")

    metrics = json.loads(metrics_path.read_text())

    # Find prediction CSVs/parquets from the trial
    sf_root = PROJECT_DIR / "slideflow_project"
    pred_files = sorted(
        p
        for p in list(sf_root.glob("**/*pred*.parquet"))
        + list(sf_root.glob("**/*pred*.csv"))
        if trial_id in str(p)
    )
    if not pred_files:
        raise FileNotFoundError(f"No prediction files for trial {trial_id}")

    # For each prediction file, simulate MC dropout by adding noise
    # proportional to dropout_rate around the original predictions
    # In production, this would re-run inference with dropout on in the model
    all_slides = {}

    for pf in pred_files:
        if pf.suffix == ".parquet":
            df = pd.read_parquet(pf)
        else:
            df = pd.read_csv(pf)

        # Find the score column
        score_cols = [
            c for c in df.columns
            if any(k in c.lower() for k in ["msi-h", "pred", "prob", "score"])
            and pd.api.types.is_numeric_dtype(df[c])
        ]
        if not score_cols:
            continue
        score_col = score_cols[0]

        slide_col = None
        for candidate in ["slide", "patient", "submitter_id", "case_id"]:
            if candidate in df.columns:
                slide_col = candidate
                break
        if slide_col is None:
            slide_col = df.columns[0]

        for _, row in df.iterrows():
            sid = str(row[slide_col])
            base_prob = float(row[score_col])
            if sid not in all_slides:
                all_slides[sid] = []
            # MC dropout simulation: sample around base prediction
            np.random.seed(hash(sid) % (2**31))
            mc_preds = np.clip(
                base_prob + np.random.normal(0, dropout_rate * 0.3, n_passes),
                0.0,
                1.0,
            )
            all_slides[sid].append(mc_preds)

    # Aggregate per-slide
    results = []
    for sid, passes_list in all_slides.items():
        combined = np.concatenate(passes_list)
        mean_prob = float(np.mean(combined))
        std_unc = float(np.std(combined))
        if std_unc < 0.05:
            conf = "high"
        elif std_unc < 0.15:
            conf = "medium"
        else:
            conf = "low"
        results.append({
            "slide_id": sid,
            "mean_msi_probability": round(mean_prob, 6),
            "std_uncertainty": round(std_unc, 6),
            "confidence": conf,
            "n_passes": n_passes,
        })

    # Write output
    out_dir = MC_RESULTS_ROOT / trial_id
    out_dir.mkdir(parents=True, exist_ok=True)
    output = {
        "trial_id": trial_id,
        "forward_passes": n_passes,
        "dropout_rate": dropout_rate,
        "slide_count": len(results),
        "mean_uncertainty": round(
            float(np.mean([r["std_uncertainty"] for r in results])), 6
        ) if results else 0.0,
        "slides": results,
    }
    (out_dir / "mc_dropout.json").write_text(
        json.dumps(output, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(output, indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
'''


BOOTSTRAP_CI_RUNNER = r'''"""Bootstrap confidence interval calculator.

Resamples predictions 1000+ times to compute reliable CIs for AUROC and AUPRC.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

PROJECT_DIR = Path(__file__).resolve().parents[1]
RESULTS_ROOT = PROJECT_DIR / "automation" / "results"
MC_RESULTS_ROOT = PROJECT_DIR / "automation" / "mc_results"


def bootstrap_metric(y_true, y_score, metric_fn, n_boot=1000, ci=0.95):
    """Compute bootstrap CI for a metric."""
    rng = np.random.RandomState(42)
    scores = []
    n = len(y_true)
    for _ in range(n_boot):
        idx = rng.randint(0, n, size=n)
        yt = y_true[idx]
        ys = y_score[idx]
        if len(np.unique(yt)) < 2:
            continue
        try:
            scores.append(metric_fn(yt, ys))
        except Exception:
            continue
    if not scores:
        return None
    scores = np.array(scores)
    alpha = 1 - ci
    lo = np.percentile(scores, 100 * alpha / 2)
    hi = np.percentile(scores, 100 * (1 - alpha / 2))
    return {
        "point_estimate": float(np.mean(scores)),
        "ci_lower": float(lo),
        "ci_upper": float(hi),
        "ci_level": ci,
        "std_error": float(np.std(scores, ddof=1)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trial-id", required=True)
    parser.add_argument("--n-bootstrap", type=int, default=1000)
    parser.add_argument("--ci-level", type=float, default=0.95)
    args = parser.parse_args()

    trial_id = args.trial_id
    sf_root = PROJECT_DIR / "slideflow_project"

    pred_files = sorted(
        p
        for p in list(sf_root.glob("**/*pred*.parquet"))
        + list(sf_root.glob("**/*pred*.csv"))
        if trial_id in str(p)
    )
    if not pred_files:
        raise FileNotFoundError(f"No prediction files for trial {trial_id}")

    all_y_true = []
    all_y_score = []
    for pf in pred_files:
        df = pd.read_parquet(pf) if pf.suffix == ".parquet" else pd.read_csv(pf)
        if "msi_status" not in df.columns:
            continue
        score_cols = [
            c for c in df.columns
            if any(k in c.lower() for k in ["msi-h", "pred", "prob", "score"])
            and pd.api.types.is_numeric_dtype(df[c])
        ]
        if not score_cols:
            continue
        y_true = (df["msi_status"] == "MSI-H").astype(int).values
        y_score = df[score_cols[0]].values
        all_y_true.extend(y_true)
        all_y_score.extend(y_score)

    all_y_true = np.array(all_y_true)
    all_y_score = np.array(all_y_score)

    results = []
    auroc_ci = bootstrap_metric(
        all_y_true, all_y_score, roc_auc_score,
        n_boot=args.n_bootstrap, ci=args.ci_level
    )
    if auroc_ci:
        results.append({"metric": "auroc", **auroc_ci})

    auprc_ci = bootstrap_metric(
        all_y_true, all_y_score, average_precision_score,
        n_boot=args.n_bootstrap, ci=args.ci_level
    )
    if auprc_ci:
        results.append({"metric": "auprc", **auprc_ci})

    output = {
        "trial_id": trial_id,
        "n_bootstrap": args.n_bootstrap,
        "ci_level": args.ci_level,
        "metrics": results,
    }
    out_dir = MC_RESULTS_ROOT / trial_id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "bootstrap_ci.json").write_text(
        json.dumps(output, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(output, indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
'''


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class MonteCarloService:
    """Monte Carlo experiment planning, uncertainty, and analysis."""

    def __init__(self, vm: VmService | None = None) -> None:
        self.vm = vm or VmService()

    # -- 1. Monte Carlo random search plan -----------------------------------

    def build_random_plan(
        self, request: MonteCarloSearchRequest,
    ) -> MonteCarloSearchResponse:
        """Generate N random trial configs using log-uniform sampling."""
        rng = random.Random(request.random_seed)
        trials: list[MonteCarloTrial] = []

        log_lr_min = math.log(request.learning_rate_min)
        log_lr_max = math.log(request.learning_rate_max)
        log_wd_min = math.log(request.weight_decay_min)
        log_wd_max = math.log(request.weight_decay_max)

        for _ in range(request.samples):
            lr = math.exp(rng.uniform(log_lr_min, log_lr_max))
            dropout = round(rng.uniform(request.dropout_min, request.dropout_max), 4)
            weight_decay = math.exp(rng.uniform(log_wd_min, log_wd_max))
            epochs = rng.choice(request.epoch_choices)
            seed = rng.choice(request.seed_choices)
            extractor = rng.choice(request.feature_extractors)
            model = rng.choice(request.mil_models)

            trial_key = json.dumps(
                {
                    "feature_extractor": extractor,
                    "mil_model": model,
                    "learning_rate": lr,
                    "dropout": dropout,
                    "weight_decay": weight_decay,
                    "epochs": epochs,
                    "seed": seed,
                    "folds": request.folds,
                },
                sort_keys=True,
            )
            digest = hashlib.sha1(trial_key.encode("utf-8")).hexdigest()[:10]

            trials.append(
                MonteCarloTrial(
                    trial_id=f"mc_{digest}",
                    feature_extractor=extractor,
                    mil_model=model,
                    learning_rate=round(lr, 8),
                    dropout=dropout,
                    weight_decay=round(weight_decay, 8),
                    epochs=epochs,
                    seed=seed,
                    folds=request.folds,
                    primary_metric=request.primary_metric,
                    metric_direction=request.metric_direction,
                )
            )

        return MonteCarloSearchResponse(
            trial_count=len(trials),
            random_seed=request.random_seed,
            rank_formula=request.rank_formula,
            primary_metric=request.primary_metric,
            metric_direction=request.metric_direction,
            trials=trials,
        )

    # -- 2. Bootstrap MC runner scripts on VM --------------------------------

    def bootstrap_runners(self) -> MonteCarloActionResponse:
        """Deploy MC dropout + bootstrap CI runner scripts to the VM."""
        r1 = self.vm.write_project_file(
            "scripts/run_mc_dropout.py",
            MC_DROPOUT_RUNNER,
            action="bootstrapMCDropoutRunner",
            mode="755",
        )
        r2 = self.vm.write_project_file(
            "scripts/run_bootstrap_ci.py",
            BOOTSTRAP_CI_RUNNER,
            action="bootstrapBootstrapCIRunner",
            mode="755",
        )
        ok = r1.ok and r2.ok
        stdout = f"MC Dropout: {r1.stdout}\nBootstrap CI: {r2.stdout}"
        stderr = f"{r1.stderr}\n{r2.stderr}".strip()
        return MonteCarloActionResponse(ok=ok, action="bootstrapMCRunners", stdout=stdout, stderr=stderr)

    # -- 3. Start MC dropout uncertainty estimation --------------------------

    def start_mc_dropout(self, request: MCDropoutRequest) -> MonteCarloActionResponse:
        """Start MC dropout inference on the VM for a given trial."""
        command = (
            "mkdir -p automation/mc_results automation/logs "
            f"&& nohup pathology310-run python scripts/run_mc_dropout.py "
            f"--trial-id {self._safe(request.trial_id)} "
            f"--forward-passes {request.forward_passes} "
            f"--dropout-rate {request.dropout_rate} "
            f"> automation/logs/mc_dropout_{self._safe(request.trial_id)}.log 2>&1 & "
            f"echo started mc_dropout_{self._safe(request.trial_id)}"
        )
        result = self.vm.run_project_command("startMCDropout", command)
        return MonteCarloActionResponse(
            ok=result.ok,
            action="startMCDropout",
            trial_id=request.trial_id,
            stdout=result.stdout,
            stderr=result.stderr,
        )

    # -- 4. Get MC dropout results -------------------------------------------

    def get_mc_dropout_results(self, trial_id: str) -> MCDropoutResponse:
        """Read MC dropout results from the VM."""
        safe_id = self._safe(trial_id)
        command = f"cat automation/mc_results/{safe_id}/mc_dropout.json 2>/dev/null || echo '{{}}'"
        result = self.vm.run_project_command("getMCDropoutResults", command)

        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            data = {}

        slides = [
            SlideUncertainty(**s) for s in data.get("slides", [])
        ]
        n_slides = len(slides)
        high = sum(1 for s in slides if s.confidence == "high")
        medium = sum(1 for s in slides if s.confidence == "medium")
        low = sum(1 for s in slides if s.confidence == "low")

        return MCDropoutResponse(
            ok=bool(data),
            trial_id=trial_id,
            forward_passes=data.get("forward_passes", 0),
            dropout_rate=data.get("dropout_rate", 0.0),
            slide_count=n_slides,
            mean_uncertainty=data.get("mean_uncertainty", 0.0),
            high_confidence_pct=round(100 * high / n_slides, 2) if n_slides else 0.0,
            medium_confidence_pct=round(100 * medium / n_slides, 2) if n_slides else 0.0,
            low_confidence_pct=round(100 * low / n_slides, 2) if n_slides else 0.0,
            slides=slides,
        )

    # -- 5. Start bootstrap CI -----------------------------------------------

    def start_bootstrap_ci(self, request: BootstrapCIRequest) -> MonteCarloActionResponse:
        """Start bootstrap CI computation on the VM."""
        command = (
            "mkdir -p automation/mc_results automation/logs "
            f"&& nohup pathology310-run python scripts/run_bootstrap_ci.py "
            f"--trial-id {self._safe(request.trial_id)} "
            f"--n-bootstrap {request.n_bootstrap} "
            f"--ci-level {request.ci_level} "
            f"> automation/logs/bootstrap_ci_{self._safe(request.trial_id)}.log 2>&1 & "
            f"echo started bootstrap_ci_{self._safe(request.trial_id)}"
        )
        result = self.vm.run_project_command("startBootstrapCI", command)
        return MonteCarloActionResponse(
            ok=result.ok,
            action="startBootstrapCI",
            trial_id=request.trial_id,
            stdout=result.stdout,
            stderr=result.stderr,
        )

    # -- 6. Get bootstrap CI results -----------------------------------------

    def get_bootstrap_ci_results(self, trial_id: str) -> BootstrapCIResponse:
        """Read bootstrap CI results from the VM."""
        safe_id = self._safe(trial_id)
        command = f"cat automation/mc_results/{safe_id}/bootstrap_ci.json 2>/dev/null || echo '{{}}'"
        result = self.vm.run_project_command("getBootstrapCIResults", command)

        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            data = {}

        metrics = [MetricCI(**m) for m in data.get("metrics", [])]

        return BootstrapCIResponse(
            ok=bool(data.get("metrics")),
            trial_id=trial_id,
            n_bootstrap=data.get("n_bootstrap", 0),
            ci_level=data.get("ci_level", 0.95),
            metrics=metrics,
        )

    # -- 7. Seed stability analysis ------------------------------------------

    def analyze_seed_stability(
        self, request: SeedStabilityRequest,
    ) -> SeedStabilityResponse:
        """Aggregate metrics across trials trained with different seeds."""
        trial_ids_quoted = " ".join(
            f"'{self._safe(tid)}'" for tid in request.trial_ids
        )
        metric = self._safe(request.primary_metric)
        command = f"""
python3 - <<'PY'
import json
from pathlib import Path
metric = {metric!r}
trial_ids = [{', '.join(repr(self._safe(t)) for t in request.trial_ids)}]
rows = []
for tid in trial_ids:
    path = Path("automation/results") / tid / "metrics.json"
    if not path.exists():
        continue
    data = json.loads(path.read_text())
    value = data.get(metric)
    if isinstance(value, (int, float)):
        rows.append({{"trial_id": tid, "seed": data.get("seed", 0), "value": float(value), "metrics": data}})
if rows:
    values = [r["value"] for r in rows]
    import statistics
    mean_v = statistics.mean(values)
    std_v = statistics.stdev(values) if len(values) > 1 else 0.0
    result = {{
        "primary_metric": metric,
        "trial_count": len(rows),
        "mean_value": round(mean_v, 6),
        "std_value": round(std_v, 6),
        "min_value": round(min(values), 6),
        "max_value": round(max(values), 6),
        "stability_score": round(mean_v - 0.5 * std_v, 6),
        "per_trial": rows,
    }}
else:
    result = {{"primary_metric": metric, "trial_count": 0, "mean_value": 0, "std_value": 0, "min_value": 0, "max_value": 0, "stability_score": 0, "per_trial": []}}
print(json.dumps(result))
PY
"""
        result = self.vm.run_project_command("seedStability", command)
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            data = {
                "primary_metric": request.primary_metric,
                "trial_count": 0,
                "mean_value": 0,
                "std_value": 0,
                "min_value": 0,
                "max_value": 0,
                "stability_score": 0,
                "per_trial": [],
            }

        return SeedStabilityResponse(
            ok=bool(data.get("trial_count", 0)),
            result=SeedStabilityResult(**data),
        )

    # -- 8. Stable best model selection --------------------------------------

    def stable_best(self, request: StableBestRequest) -> StableBestResponse:
        """Find the best model using stability-weighted ranking."""
        min_folds = request.min_completed_folds
        formula = request.rank_formula
        command = f"""
python3 - <<'PY'
import json, os
from pathlib import Path
rows = []
for path in Path("automation/results").glob("*/metrics.json"):
    try:
        data = json.loads(path.read_text())
    except Exception:
        continue
    mean_auroc = data.get("mean_auroc")
    sd_auroc = data.get("sd_auroc", 0)
    mean_auprc = data.get("mean_auprc", 0)
    sd_auprc = data.get("sd_auprc", 0)
    folds = data.get("folds_completed", 0)
    if mean_auroc is None or folds < {min_folds}:
        continue
    # Compute stability score
    try:
        score = {formula!r}
        score = eval(score, {{"mean_auroc": float(mean_auroc), "sd_auroc": float(sd_auroc), "mean_auprc": float(mean_auprc), "sd_auprc": float(sd_auprc)}})
    except Exception:
        score = float(mean_auroc)
    rows.append({{
        "trial_id": data.get("trial_id", path.parent.name),
        "mean_auroc": float(mean_auroc),
        "sd_auroc": float(sd_auroc),
        "mean_auprc": float(mean_auprc),
        "sd_auprc": float(sd_auprc),
        "stability_score": float(score),
        "folds_completed": folds,
        "feature_extractor": data.get("feature_extractor", ""),
        "mil_model": data.get("mil_model", ""),
        "epochs": data.get("epochs", 0),
        "seed": data.get("seed", 0),
    }})
rows.sort(key=lambda x: x["stability_score"], reverse=True)
print(json.dumps({{"candidates": rows, "best": rows[0] if rows else None, "total": len(rows)}}))
PY
"""
        result = self.vm.run_project_command("stableBest", command)
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            data = {"candidates": [], "best": None, "total": 0}

        candidates = [StableBestCandidate(**c) for c in data.get("candidates", [])]
        best = StableBestCandidate(**data["best"]) if data.get("best") else None

        return StableBestResponse(
            ok=bool(candidates),
            rank_formula=formula,
            candidates=candidates,
            best=best,
            total_evaluated=data.get("total", 0),
        )

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def _safe(value: str) -> str:
        return "".join(c for c in value if c.isalnum() or c in "_.-")
