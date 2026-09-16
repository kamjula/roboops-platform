# Predictive-maintenance ML

RoboOps builds predictive-maintenance capability in stages so the repository does not claim model performance that the available data cannot support.

## Current implemented foundation

The backend feature service reads persisted PostgreSQL telemetry and builds hourly feature rows from battery and temperature readings. Each feature row is derived only from readings inside that historical hour. The service reports complete and incomplete windows explicitly and excludes windows that do not meet the minimum sample count for both supported sensor types.

Current features per hourly robot window:

- battery reading count, mean, minimum, maximum, and sample standard deviation
- temperature reading count, mean, minimum, maximum, and sample standard deviation

The extraction query is set-based in PostgreSQL and supports an optional robot scope and bounded lookback window.

## What RoboOps does not claim yet

RoboOps does not currently claim supervised failure prediction, remaining useful life, accuracy, precision, recall, ROC-AUC, or any other supervised-model metric.

The existing `maintenance_records` table describes completed maintenance work, but it does not contain a verified failure outcome label. Treating every maintenance record as a failure would create a false training target because preventive, scheduled, and corrective maintenance are not equivalent outcomes.

## Training gate

A supervised predictive-maintenance model may be added only after one of these defensible label sources is available:

1. Product telemetry is joined to an explicit, verified failure/breakdown outcome with a known event timestamp and label definition; or
2. A reputable public predictive-maintenance benchmark is used for model evaluation, clearly identified as external benchmark data and kept separate from RoboOps production telemetry claims.

Any future supervised evaluation must use time-aware train/validation/test splits so future observations do not leak into earlier training examples.

## Next implementation steps

The next ML increment will consume the feature dataset through a reproducible training interface. If product failure labels are still unavailable, the platform may add an unsupervised condition/anomaly model trained on actual persisted telemetry, but it will be described as anomaly or condition scoring rather than failure prediction. Model artifacts must include version metadata, feature schema, training window, and evaluation metadata before they can be used by an inference endpoint.
