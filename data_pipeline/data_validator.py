"""Validate required columns and numeric values in tabular data."""

import logging
import math

import pandas as pd


logger = logging.getLogger(__name__)


def validate_dataframe(df, required_columns, numeric_columns):
    """Return a copy containing required columns and valid numeric data."""
    # Find required column names that are missing from the table.
    missing_columns = [
        column for column in required_columns if column not in df.columns
    ]

    # Stop validation when a required column is missing.
    if missing_columns:
        message = f"Required columns are missing: {missing_columns}"
        logger.error(message)
        raise ValueError(message)

    # Copy the table before changing types or removing rows.
    validated = df.copy()
    rows_before = len(validated)

    # Check each configured numeric column and discard invalid values.
    for column in numeric_columns:
        if column not in validated.columns:
            message = f"Numeric column not found: {column}"
            logger.error(message)
            raise ValueError(message)

        # Mark each non-blank value that cannot be read as a finite number.
        invalid_mask = []
        for value in validated[column]:
            invalid = False
            if pd.notna(value):
                try:
                    number = float(value)
                except (TypeError, ValueError):
                    invalid = True
                else:
                    invalid = not math.isfinite(number)
            invalid_mask.append(invalid)

        invalid_count = sum(invalid_mask)
        if invalid_count:
            logger.warning(
                "Removed %s rows with invalid numeric values in %s",
                invalid_count,
                column,
            )
            # Use row positions so duplicate index labels are handled correctly.
            validated = validated.iloc[
                [not invalid for invalid in invalid_mask]
            ].copy()

        # Convert the remaining values to a numeric column for later processing.
        validated[column] = pd.to_numeric(validated[column])

    # Record how many rows passed the checks.
    logger.debug(
        "Validation: %s -> %s rows (%s removed)",
        rows_before,
        len(validated),
        rows_before - len(validated),
    )
    return validated