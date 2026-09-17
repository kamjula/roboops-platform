"""Integrate telemetry feature extraction with unsupervised condition scoring."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.services.predictive_feature_service import build_predictive_feature_dataset
from app.services.telemetry_condition_model import MIN_BASELINE_ROWS, fit_feature_baseline, score_condition

CONDITION_MODEL_VERSION = "rms-z-v1"
CONDITION_METHOD = "rms_z_score"


def get_robot_condition(
    db: Session,
    *,
    robot_id: uuid.UUID,
    as_of: datetime | None = None,
    lookback_hours: int = 168,
) -> dict:
    """Score the newest complete hourly feature row against preceding real rows.

    The newest row is never included in its own baseline. This endpoint reports
    telemetry condition only; it does not predict failure probability or RUL.
    """
    dataset = build_predictive_feature_dataset(
        db,
        as_of=as_of,
        lookback_hours=lookback_hours,
        robot_id=robot_id,
    )
    rows = dataset["feature_rows"]
    audit = {
        "as_of": dataset["as_of"],
        "window_start": dataset["window_start"],
        "condition_model_version": CONDITION_MODEL_VERSION,
        "method": CONDITION_METHOD,
        "predicts_failure": False,
    }
    if not rows:
        return {
            "robot_id": robot_id,
            "status": "unknown",
            "score": None,
            "reason": "no_complete_feature_rows",
            "feature_z_scores": {},
            "baseline_row_count": 0,
            "candidate_bucket_start": None,
            "lookback_hours": lookback_hours,
            **audit,
        }

    candidate = rows[-1]
    baseline_rows = rows[:-1]
    if len(baseline_rows) < MIN_BASELINE_ROWS:
        return {
            "robot_id": robot_id,
            "status": "unknown",
            "score": None,
            "reason": "minimum_baseline_rows_not_met",
            "feature_z_scores": {},
            "baseline_row_count": len(baseline_rows),
            "candidate_bucket_start": candidate["bucket_start"],
            "lookback_hours": lookback_hours,
            **audit,
        }

    baseline = fit_feature_baseline(baseline_rows)
    result = score_condition(candidate, baseline)
    return {
        "robot_id": robot_id,
        "status": result.status,
        "score": result.score,
        "reason": result.reason,
        "feature_z_scores": result.feature_z_scores,
        "baseline_row_count": baseline.row_count,
        "candidate_bucket_start": candidate["bucket_start"],
        "lookback_hours": lookback_hours,
        **audit,
    }
