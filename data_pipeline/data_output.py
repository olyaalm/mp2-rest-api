"""Functions for writing processed data to disk."""

import logging
from pathlib import Path


logger = logging.getLogger(__name__)


def save_data(df, filepath):
    """Write a DataFrame to a CSV file and return the path used.

    Args:
        df: Table to save.
        filepath: Destination path for the CSV file.

    Returns:
        Path: Destination path after the file is written.

    Raises:
        OSError: If a parent folder or the output file cannot be created.
    """
    # Convert the output name to a path and create missing parent folders.
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write the table without its pandas row index.
    df.to_csv(path, index=False)
    logger.debug("Saved %s rows to %s", len(df), path)
    return path