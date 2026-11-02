import logging


def setup_logging(verbose=False):
    """Set the shared log level and message format.

    Args:
        verbose: When True, include debug messages; otherwise use info level.

    Returns:
        None: Configures Python's root logger in place.
    """
    # Use detailed messages in development and normal progress logs otherwise.
    level = logging.DEBUG if verbose else logging.INFO

    # Keep one consistent timestamp, level, logger name, and message layout.
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )