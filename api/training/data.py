from __future__ import annotations

import pandas as pd

from api.training.config import TrainingConfig, resolve_repo_path


def load_dataset(config: TrainingConfig) -> pd.DataFrame:
    dataset_path = resolve_repo_path(config.data.dataset_path)
    if not dataset_path.exists():
        raise FileNotFoundError(
            f"Dataset not found at '{dataset_path}'. Add the simulation dataset first."
        )

    suffix = dataset_path.suffix.lower()
    if suffix == ".csv" or config.data.file_format.lower() == "csv":
        dataframe = pd.read_csv(dataset_path)
    elif suffix == ".parquet" or config.data.file_format.lower() == "parquet":
        dataframe = pd.read_parquet(dataset_path)
    else:
        raise ValueError(
            "Unsupported dataset format. Use CSV or Parquet and update the config."
        )

    if config.data.sample_rows > 0:
        dataframe = dataframe.head(config.data.sample_rows).copy()

    if dataframe.empty:
        raise ValueError("Loaded dataset is empty.")

    return dataframe


def annotate_trip_start(dataframe: pd.DataFrame, config: TrainingConfig) -> pd.DataFrame:
    trip_column = config.data.trip_id_column
    scheduled_column = config.data.scheduled_time_column
    missing_columns = [
        column
        for column in (trip_column, scheduled_column)
        if column not in dataframe.columns
    ]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"Dataset is missing required trip columns: {missing}.")

    frame = dataframe.copy()
    frame["trip_start_scheduled_unix"] = (
        frame.groupby(trip_column, sort=False)[scheduled_column].transform("min")
    )
    return frame


def derive_segment_dataset(
    dataframe: pd.DataFrame, config: TrainingConfig
) -> pd.DataFrame:
    trip_column = config.data.trip_id_column
    route_column = config.data.route_id_column
    stop_column = config.data.stop_id_column
    sequence_column = config.data.stop_sequence_column
    scheduled_column = config.data.scheduled_time_column
    actual_column = config.data.actual_time_column

    required_columns = [
        trip_column,
        route_column,
        stop_column,
        sequence_column,
        scheduled_column,
        actual_column,
    ]
    missing_columns = [
        column for column in required_columns if column not in dataframe.columns
    ]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"Dataset is missing required segment columns: {missing}.")

    frame = annotate_trip_start(dataframe, config)
    frame = frame.sort_values(
        [trip_column, sequence_column, scheduled_column]
    ).reset_index(drop=True)

    grouped = frame.groupby(trip_column, sort=False)
    frame["from_stop_id"] = grouped[stop_column].shift(1)
    frame["to_stop_id"] = frame[stop_column]
    frame["prev_scheduled_arrival_unix"] = grouped[scheduled_column].shift(1)
    frame["prev_gps_timestamp"] = grouped[actual_column].shift(1)
    frame["segment_start_scheduled_unix"] = frame["prev_scheduled_arrival_unix"]

    frame["scheduled_segment_minutes"] = (
        frame[scheduled_column] - frame["prev_scheduled_arrival_unix"]
    ) / 60.0
    frame["actual_segment_minutes"] = (
        frame[actual_column] - frame["prev_gps_timestamp"]
    ) / 60.0
    frame["segment_delay_minutes"] = (
        frame["actual_segment_minutes"] - frame["scheduled_segment_minutes"]
    )

    segment_frame = frame[frame["from_stop_id"].notna()].copy()
    segment_grouped = segment_frame.groupby(trip_column, sort=False)
    previous_segment_delay = segment_grouped["segment_delay_minutes"].shift(1)
    segment_frame["prev_segment_delay"] = previous_segment_delay.fillna(0.0)
    segment_frame["rolling_segment_delay_3"] = (
        previous_segment_delay.groupby(segment_frame[trip_column], sort=False)
        .transform(lambda values: values.rolling(window=3, min_periods=1).mean())
        .fillna(0.0)
    )

    numeric_columns = [
        "segment_start_scheduled_unix",
        "scheduled_segment_minutes",
        "actual_segment_minutes",
        "segment_delay_minutes",
        "prev_segment_delay",
        "rolling_segment_delay_3",
    ]
    for column in numeric_columns:
        segment_frame[column] = pd.to_numeric(segment_frame[column], errors="raise")

    segment_frame = segment_frame.reset_index(drop=True)

    if segment_frame.empty:
        raise ValueError(
            "Segment derivation returned an empty dataframe. Check the stop ordering."
        )

    return segment_frame


def take_group_row_budget(
    dataframe: pd.DataFrame,
    group_column: str,
    sort_column: str,
    sample_rows: int,
) -> pd.DataFrame:
    if sample_rows <= 0 or sample_rows >= len(dataframe):
        return dataframe.copy()

    if group_column not in dataframe.columns or sort_column not in dataframe.columns:
        return dataframe.head(sample_rows).copy()

    group_sizes = dataframe.groupby(group_column, sort=False).size()
    group_order = (
        dataframe[[group_column, sort_column]]
        .drop_duplicates(subset=[group_column])
        .sort_values(sort_column)
    )

    selected_groups: list[str | int | float] = []
    selected_rows = 0
    for group_value in group_order[group_column].tolist():
        selected_groups.append(group_value)
        selected_rows += int(group_sizes.loc[group_value])
        if selected_rows >= sample_rows:
            break

    return dataframe[dataframe[group_column].isin(selected_groups)].copy()


def _compute_split_indices(total_items: int, config: TrainingConfig) -> tuple[int, int]:
    train_end = int(total_items * config.split.train_fraction)
    validation_end = train_end + int(total_items * config.split.validation_fraction)
    return train_end, validation_end


def _validate_split_fractions(config: TrainingConfig) -> None:
    total_fraction = (
        config.split.train_fraction
        + config.split.validation_fraction
        + config.split.test_fraction
    )
    if abs(total_fraction - 1.0) > 1e-9:
        raise ValueError("Train, validation, and test fractions must sum to 1.0.")


def split_dataset(
    dataframe: pd.DataFrame, config: TrainingConfig
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    _validate_split_fractions(config)

    group_column = config.split.group_by
    sort_column = config.split.sort_by

    if group_column and group_column in dataframe.columns:
        if sort_column and sort_column in dataframe.columns:
            group_order = (
                dataframe[[group_column, sort_column]]
                .drop_duplicates(subset=[group_column])
                .sort_values(sort_column)
                .reset_index(drop=True)
            )
        else:
            group_order = pd.DataFrame(
                {group_column: dataframe[group_column].drop_duplicates().tolist()}
            )

        total_groups = len(group_order)
        train_end, validation_end = _compute_split_indices(total_groups, config)

        train_groups = set(group_order.iloc[:train_end][group_column].tolist())
        validation_groups = set(
            group_order.iloc[train_end:validation_end][group_column].tolist()
        )
        test_groups = set(group_order.iloc[validation_end:][group_column].tolist())

        train_frame = dataframe[dataframe[group_column].isin(train_groups)].copy()
        validation_frame = dataframe[
            dataframe[group_column].isin(validation_groups)
        ].copy()
        test_frame = dataframe[dataframe[group_column].isin(test_groups)].copy()
    else:
        if sort_column and sort_column in dataframe.columns:
            sorted_frame = dataframe.sort_values(sort_column).reset_index(drop=True)
        else:
            sorted_frame = dataframe.reset_index(drop=True)

        row_count = len(sorted_frame)
        train_end, validation_end = _compute_split_indices(row_count, config)
        train_frame = sorted_frame.iloc[:train_end].copy()
        validation_frame = sorted_frame.iloc[train_end:validation_end].copy()
        test_frame = sorted_frame.iloc[validation_end:].copy()

    if train_frame.empty or validation_frame.empty or test_frame.empty:
        raise ValueError(
            "One of the train/validation/test splits is empty. Adjust the split config."
        )

    return train_frame, validation_frame, test_frame
