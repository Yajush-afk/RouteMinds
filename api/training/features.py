from __future__ import annotations

import pandas as pd

from training.config import FeatureConfig, TrainingConfig


def derive_time_features(
    dataframe: pd.DataFrame, config: TrainingConfig
) -> pd.DataFrame:
    timestamp_column = config.data.actual_time_column
    if not timestamp_column or timestamp_column not in dataframe.columns:
        return dataframe

    frame = dataframe.copy()
    timestamps = pd.to_datetime(frame[timestamp_column], unit="s", errors="coerce")

    if "hour_of_day" not in frame.columns:
        frame["hour_of_day"] = timestamps.dt.hour
    if "day_of_week" not in frame.columns:
        frame["day_of_week"] = timestamps.dt.dayofweek

    return frame


def validate_feature_columns(
    dataframe: pd.DataFrame,
    feature_config: FeatureConfig,
    target_column: str,
) -> None:
    expected_columns = (
        set(feature_config.categorical)
        | set(feature_config.numeric)
        | {target_column}
    )

    missing_columns = sorted(
        column for column in expected_columns if column not in dataframe.columns
    )
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"Dataset is missing configured columns: {missing}.")


def build_training_frame(
    dataframe: pd.DataFrame,
    feature_config: FeatureConfig,
    target_column: str,
) -> tuple[pd.DataFrame, pd.Series]:
    validate_feature_columns(dataframe, feature_config, target_column)

    drop_columns = [
        column for column in feature_config.drop if column in dataframe.columns
    ]
    feature_columns = feature_config.categorical + feature_config.numeric

    cleaned_frame = dataframe.drop(columns=drop_columns).copy()
    cleaned_frame = cleaned_frame.dropna(subset=[target_column])

    feature_frame = cleaned_frame[feature_columns].copy()
    target = cleaned_frame[target_column].copy()

    return feature_frame, target
