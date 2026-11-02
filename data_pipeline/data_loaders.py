"""Reading CSV, JSON, and YAML files for the reusable MP1 pipeline."""

import json
import logging
from pathlib import Path

import pandas as pd
import yaml


logger = logging.getLogger(__name__)


def load_csv(filepath):
    """Read a CSV file into a pandas table.

    Args:
        filepath: Path to the CSV file.

    Returns:
        DataFrame: The CSV rows and columns.

    Raises:
        OSError: If the file cannot be opened.
        pandas.errors.ParserError: If the CSV structure is invalid.
    """
    # Read CSV rows into a table with named columns.
    data = pd.read_csv(filepath)
    logger.info("Loaded CSV file: %s (%s rows)", filepath, len(data))
    return data


def load_json(filepath):
    """Read a JSON file and convert its text into Python data.

    Args:
        filepath: Path to the JSON file.

    Returns:
        object: The Python value represented by the JSON file.

    Raises:
        OSError: If the file cannot be opened.
        json.JSONDecodeError: If the file does not contain valid JSON.
    """
    # Open the file and turn its JSON text into Python data.
    with filepath.open(encoding="utf-8") as file:
        data = json.load(file)
    logger.info("Loaded JSON file: %s", filepath)
    return data


def load_yaml(filepath):
    """Read a YAML file and safely convert its text into Python data.

    Args:
        filepath: Path to the YAML file.

    Returns:
        object: The Python value represented by the YAML file.

    Raises:
        OSError: If the file cannot be opened.
        ValueError: If the file contains invalid YAML.
    """
    # Open the file and safely turn its YAML text into Python data.
    with filepath.open(encoding="utf-8") as file:
        try:
            data = yaml.safe_load(file)
        except yaml.YAMLError as error:
            logger.error("Invalid YAML file: %s", filepath)
            raise ValueError(f"Invalid YAML file: {filepath}") from error
    logger.info("Loaded YAML file: %s", filepath)
    return data


def load_data(filepath):
    """Choose a file reader based on the file extension.

    Args:
        filepath: Path to a CSV, JSON, or YAML file.

    Returns:
        object: A DataFrame for CSV, or Python data for JSON/YAML.

    Raises:
        ValueError: If the extension is not supported.
        OSError: If the selected file cannot be opened.
    """
    # Normalize the path and extension before choosing a file reader.
    path = Path(filepath)
    extension = path.suffix.lower()

    # Match each supported file ending to its loading function.
    loaders = {
        ".csv": load_csv,
        ".json": load_json,
        ".yaml": load_yaml,
    }

    # Give a clear error if there is no loader for this file type.
    loader = loaders.get(extension)
    if loader is None:
        logger.error("Unsupported file format: %s", extension)
        raise ValueError(f"Unsupported file format: {extension}")

    return loader(path)