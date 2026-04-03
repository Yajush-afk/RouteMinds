from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import tomllib

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(slots=True)
class DataConfig:
    dataset_path: str
    file_format: str = "parquet"
    trip_id_column: str = "trip_id"
    route_id_column: str = "route_id"
    stop_id_column: str = "stop_id"
    stop_sequence_column: str = "stop_sequence"
    scheduled_time_column: str = "scheduled_arrival_unix"
    actual_time_column: str = "gps_timestamp"
    stop_delay_column: str = "delay_minutes"
    sample_rows: int = 0


@dataclass(slots=True)
class SplitConfig:
    train_fraction: float = 0.8
    validation_fraction: float = 0.1
    test_fraction: float = 0.1
    group_by: str = "trip_id"
    sort_by: str = "trip_start_scheduled_unix"


@dataclass(slots=True)
class TargetConfig:
    canonical_target: str = "actual_segment_minutes"
    secondary_target: str = "segment_delay_minutes"
    smoke_target: str = "delay_minutes"


@dataclass(slots=True)
class FeatureConfig:
    categorical: list[str] = field(default_factory=list)
    numeric: list[str] = field(default_factory=list)
    drop: list[str] = field(default_factory=list)
    feature_time_column: str | None = None


@dataclass(slots=True)
class SmokeConfig:
    enabled: bool = True
    sample_rows: int = 200_000


@dataclass(slots=True)
class ModelConfig:
    n_estimators: int = 400
    max_depth: int = 8
    learning_rate: float = 0.05
    subsample: float = 0.85
    colsample_bytree: float = 0.85
    reg_alpha: float = 0.0
    reg_lambda: float = 1.0
    random_state: int = 42


@dataclass(slots=True)
class ArtifactConfig:
    model_path: str
    metrics_path: str
    schema_path: str
    config_snapshot_path: str
    smoke_metrics_path: str


@dataclass(slots=True)
class TrainingConfig:
    data: DataConfig
    split: SplitConfig
    targets: TargetConfig
    stop_smoke_features: FeatureConfig
    segment_features: FeatureConfig
    smoke: SmokeConfig
    model: ModelConfig
    artifacts: ArtifactConfig


def resolve_repo_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def load_training_config(config_path: str | Path) -> TrainingConfig:
    path = Path(config_path)
    if not path.is_absolute():
        repo_relative_path = REPO_ROOT / path
        api_relative_path = REPO_ROOT / "api" / path
        path = repo_relative_path if repo_relative_path.exists() else api_relative_path

    with path.open("rb") as config_file:
        raw = tomllib.load(config_file)

    return TrainingConfig(
        data=DataConfig(**raw["data"]),
        split=SplitConfig(**raw["split"]),
        targets=TargetConfig(**raw["targets"]),
        stop_smoke_features=FeatureConfig(**raw["stop_smoke_features"]),
        segment_features=FeatureConfig(**raw["segment_features"]),
        smoke=SmokeConfig(**raw.get("smoke", {})),
        model=ModelConfig(**raw["model"]),
        artifacts=ArtifactConfig(**raw["artifacts"]),
    )


def serialize_training_config(config: TrainingConfig) -> dict[str, Any]:
    return asdict(config)
