import logging

logger = logging.getLogger(__name__)


class DatasetStorage:
    """Keep uploaded DataFrames in memory and return protected copies."""

    def __init__(self):
        """Create an empty store and start dataset IDs at one.

        Returns:
            None: Initializes this storage instance.
        """
        # Map each dataset ID to its filename and saved DataFrame.
        self._store = {}
        self._counter = 0

    def save(self, df, filename):
        """Save a protected copy of a DataFrame and assign it an ID.

        Args:
            df: Table to save.
            filename: Original filename associated with the table.

        Returns:
            int: The newly assigned dataset ID.
        """
        # Give each upload a new ID and isolate stored data from caller edits.
        self._counter += 1
        dataset_id = self._counter
        self._store[dataset_id] = {"filename": filename, "data": df.copy(deep=True)}
        logger.debug("Stored dataset: id=%s, rows=%s", dataset_id, len(df))
        return dataset_id

    def get(self, dataset_id):
        """Return a copy of a saved table, or None when its ID is unknown.

        Args:
            dataset_id: ID of the dataset to retrieve.

        Returns:
            DataFrame | None: A safe copy of the table, or None if absent.
        """
        # Look up the dataset and avoid exposing the stored DataFrame directly.
        dataset = self._store.get(dataset_id)
        if dataset is None:
            logger.debug("Dataset not found in storage: id=%s", dataset_id)
            return None

        df = dataset["data"].copy(deep=True)
        logger.debug("Retrieved dataset copy: id=%s, rows=%s", dataset_id, len(df))
        return df

    def get_metadata(self, dataset_id):
        """Return a dataset's filename and shape, or None if it is absent.

        Args:
            dataset_id: ID of the dataset to describe.

        Returns:
            dict | None: Dataset metadata, or None when no dataset matches.
        """
        # Return metadata from the stored table without changing it.
        dataset = self._store.get(dataset_id)
        if dataset is None:
            logger.debug("Dataset metadata not found: id=%s", dataset_id)
            return None

        df = dataset["data"]
        return {
            "id": dataset_id,
            "filename": dataset["filename"],
            "rows": len(df),
            "columns": len(df.columns),
            "column_names": list(df.columns),
        }

    def update(self, dataset_id, df):
        """Replace a saved table with a protected copy of a new DataFrame.

        Args:
            dataset_id: ID of the dataset to replace.
            df: New table to save under the existing ID.

        Returns:
            bool: True if the dataset existed and was updated; otherwise False.
        """
        # Replace data only for an ID that already exists, storing another copy.
        dataset = self._store.get(dataset_id)
        if dataset is None:
            logger.debug("Cannot update missing dataset: id=%s", dataset_id)
            return False

        dataset["data"] = df.copy(deep=True)
        logger.debug("Updated dataset: id=%s, rows=%s", dataset_id, len(df))
        return True

    def clear(self):
        """Remove every dataset and reset the next ID to one.

        Returns:
            None: Clears this storage instance in place.
        """
        # Reset storage so tests and app restarts begin with predictable IDs.
        self._store.clear()
        self._counter = 0
        logger.debug("Cleared dataset storage")