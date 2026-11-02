import logging


def setup_logging(verbose=False):
    """Configure logging using the MP1 pipeline's log format."""
    # Use detailed messages in development and normal progress logs otherwise.
    level = logging.DEBUG if verbose else logging.INFO

    # Keep one consistent timestamp, level, logger name, and message layout.
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )