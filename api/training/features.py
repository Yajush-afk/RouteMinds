from __future__ import annotations

import pandas as pd

from api.common.features import prepare_model_frame
from api.training.config import FeatureConfig


def validate_feature_columns(
    dataframe: pd.DataFrame,
    feature_config: FeatureConfig,
    target_column: str,
) -> None:
    if target_column not in dataframe.columns:
        raise ValueError(f"Dataset is missing configured target column: {target_column}.")


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
    cleaned_frame = prepare_model_frame(
        cleaned_frame,
        categorical_columns=feature_config.categorical,
        numeric_columns=feature_config.numeric,
        feature_time_column=feature_config.feature_time_column,
    )

    feature_frame = cleaned_frame[feature_columns].copy()
    target = cleaned_frame[target_column].copy()

    return feature_frame, target
