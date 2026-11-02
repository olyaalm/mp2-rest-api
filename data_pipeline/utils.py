"""Shared logging and input-path utilities for the MP1 pipeline."""

import logging
from pathlib import Path


logger = logging.getLogger(__name__)


def setup_logging(verbose=False):
    """Set the pipeline log level and shared message format.

    Args:
        verbose: When True, include debug messages; otherwise use info level.

    Returns:
        None: Configures Python's root logger in place.
    """
    # Choose detailed messages or normal progress messages.
    level = logging.DEBUG if verbose else logging.INFO

    # Set the level and layout used by every pipeline module.
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )


def validate_input(filepath):
    """Check whether a path points to an existing regular file.

    Args:
        filepath: Path to check.

    Returns:
        bool: True when the path is a file, or False when it is missing.
    """
    # Check that the path points to a file.
    if Path(filepath).is_file():
        logger.info("Input file validated: %s", filepath)
        return True

    logger.error("Input file not found: %s", filepath)
    return False