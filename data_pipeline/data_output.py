"""Functions for writing processed data to disk."""

import logging
from pathlib import Path


logger = logging.getLogger(__name__)


def save_data(df, filepath):
    """Save a DataFrame as CSV and return its output path."""
    # Convert the output name to a path and create missing parent folders.
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write the table without its pandas row index.
    df.to_csv(path, index=False)
    logger.debug("Saved %s rows to %s", len(df), path)
    return path