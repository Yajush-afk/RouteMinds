from __future__ import annotations

import pandas as pd


def derive_temporal_features(
    dataframe: pd.DataFrame,
    feature_time_column: str | None,
) -> pd.DataFrame:
    if not feature_time_column:
        return dataframe.copy()

    if feature_time_column not in dataframe.columns:
        raise ValueError(
            "Dataset is missing the configured feature time column: "
            f"{feature_time_column}."
        )

    frame = dataframe.copy()
    timestamps = pd.to_datetime(
        frame[feature_time_column],
        unit="s",
        errors="coerce",
    )
    frame["hour_of_day"] = timestamps.dt.hour
    frame["day_of_week"] = timestamps.dt.dayofweek
    return frame


def normalize_categorical_columns(
    dataframe: pd.DataFrame,
    categorical_columns: list[str],
) -> pd.DataFrame:
    frame = dataframe.copy()
    for column in categorical_columns:
        if column in frame.columns:
            frame[column] = frame[column].astype("string")
    return frame


def prepare_model_frame(
    dataframe: pd.DataFrame,
    categorical_columns: list[str],
    numeric_columns: list[str],
    feature_time_column: str | None = None,
) -> pd.DataFrame:
    frame = derive_temporal_features(dataframe, feature_time_column)
    frame = normalize_categorical_columns(frame, categorical_columns)

    feature_columns = categorical_columns + numeric_columns
    missing_columns = [
        column for column in feature_columns if column not in frame.columns
    ]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"Dataset is missing configured columns: {missing}.")

    return frame
