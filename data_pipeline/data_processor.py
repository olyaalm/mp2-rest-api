"""Reusable data-cleaning operations for tabular datasets."""

import logging
import math

import pandas as pd


logger = logging.getLogger(__name__)


def remove_duplicates(df):
    """Remove duplicate rows while keeping the first copy."""
    # Drop rows whose values match across every column.
    cleaned = df.drop_duplicates()
    logger.debug("remove_duplicates: %s -> %s rows", len(df), len(cleaned))
    return cleaned


def handle_missing(df, axis="rows"):
    """Drop rows or columns containing missing values."""
    # Confirm that the requested direction is rows or columns.
    if not isinstance(axis, str) or axis not in {"rows", "columns"}:
        logger.error("Unsupported missing-value axis: %s", axis)
        raise ValueError(f"Unsupported missing-value axis: {axis}")

    # Drop rows or columns that contain at least one blank value.
    cleaned = df.dropna(axis=0 if axis == "rows" else 1)

    # Count the number of removed rows or columns for the debug message.
    if axis == "rows":
        removed = len(df) - len(cleaned)
    else:
        removed = len(df.columns) - len(cleaned.columns)
    logger.debug("handle_missing (%s): removed %s", axis, removed)
    return cleaned


def remove_outliers(df, columns, method, threshold):
    """Remove outliers from the specified numeric columns."""
    # Accept only the two outlier methods supported by the pipeline.
    if not isinstance(method, str) or method not in {"iqr", "zscore"}:
        logger.error("Unsupported outlier method: %s", method)
        raise ValueError(f"Unsupported outlier method: {method}")

    # Copy the table before removing any rows.
    cleaned = df.copy()

    # Check each configured column for values outside the selected limits.
    for column in columns:
        if column not in cleaned.columns:
            logger.warning("Column not found: %s", column)
            continue
        if not pd.api.types.is_numeric_dtype(cleaned[column]):
            logger.warning("Column is not numeric: %s", column)
            continue

        values = cleaned[column]
        if method == "iqr":
            # Set outlier limits using the middle half of the values.
            first_quartile = values.quantile(0.25)
            third_quartile = values.quantile(0.75)
            spread = third_quartile - first_quartile
            lower = first_quartile - threshold * spread
            upper = third_quartile + threshold * spread
            outliers = (values < lower) | (values > upper)
            logger.debug(
                "%s (iqr, threshold=%s): lower=%s, upper=%s, removed=%s",
                column,
                threshold,
                lower,
                upper,
                int(outliers.sum()),
            )
        else:
            # Find values farther from the average than the selected threshold.
            mean = values.mean()
            standard_deviation = values.std()
            if pd.isna(standard_deviation) or standard_deviation == 0:
                # A column with no spread has no z-score outliers.
                outliers = pd.Series(False, index=cleaned.index)
            else:
                outliers = (
                    (values - mean).abs() / standard_deviation
                ) > threshold
            logger.debug(
                "%s (zscore, threshold=%s): removed=%s",
                column,
                threshold,
                int(outliers.sum()),
            )

        # Keep only rows not marked as outliers for this column.
        cleaned = cleaned.loc[~outliers]

    logger.debug(
        "remove_outliers (%s, threshold=%s): removed %s rows",
        method,
        threshold,
        len(df) - len(cleaned),
    )
    return cleaned


def process_data(df, config):
    """Apply the processing steps enabled in the configuration."""
    # Read the settings that choose which cleaning steps are running.
    if not isinstance(config, dict) or not isinstance(
        config.get("processing"), dict
    ):
        raise ValueError("Configuration must include a processing mapping")
    settings = config["processing"]
    cleaned = df

    # Remove duplicate rows when that step is enabled.
    remove_duplicates_enabled = settings.get("remove_duplicates", False)
    if not isinstance(remove_duplicates_enabled, bool):
        raise ValueError("processing.remove_duplicates must be true or false")
    if remove_duplicates_enabled:
        cleaned = remove_duplicates(cleaned)

    # Read the missing-value options and apply them when enabled.
    missing = settings.get("missing", {})
    if not isinstance(missing, dict):
        raise ValueError("processing.missing must be a mapping")
    missing_enabled = missing.get("enabled", False)
    if not isinstance(missing_enabled, bool):
        raise ValueError("processing.missing.enabled must be true or false")
    if missing_enabled:
        axis = missing.get("axis")
        if not isinstance(axis, str) or axis not in {"rows", "columns"}:
            raise ValueError("Enabled missing-value handling needs axis rows or columns")
        cleaned = handle_missing(cleaned, axis=axis)

    # Read the optional outlier-removal settings.
    outliers = settings.get("outliers", {})
    if not isinstance(outliers, dict):
        raise ValueError("processing.outliers must be a mapping")
    outliers_enabled = outliers.get("enabled", False)
    if not isinstance(outliers_enabled, bool):
        raise ValueError("processing.outliers.enabled must be true or false")
    if outliers_enabled:
        columns = outliers.get("columns")
        method = outliers.get("method")
        threshold = outliers.get("threshold")
        if not isinstance(columns, list) or any(
            not isinstance(column, str) for column in columns
        ):
            raise ValueError("Enabled outlier removal needs a list of column names")
        if not isinstance(method, str) or method not in {"iqr", "zscore"}:
            raise ValueError("Outlier method must be iqr or zscore")
        if (
            isinstance(threshold, bool)
            or not isinstance(threshold, (int, float))
            or not math.isfinite(threshold)
            or threshold < 0
        ):
            raise ValueError("Outlier threshold must be a finite non-negative number")
        cleaned = remove_outliers(
            cleaned,
            columns=columns,
            method=method,
            threshold=threshold,
        )

    return cleaned


def create_cleaning_report(df_before, df_after):
    """Summarize how many rows and columns changed during cleaning."""
    # Count rows and columns before and after the processing steps.
    rows_before = len(df_before)
    rows_after = len(df_after)
    columns_before = len(df_before.columns)
    columns_after = len(df_after.columns)
    return {
        "rows_before": rows_before,
        "rows_after": rows_after,
        "rows_removed": rows_before - rows_after,
        "columns_before": columns_before,
        "columns_after": columns_after,
        "columns_removed": columns_before - columns_after,
    }