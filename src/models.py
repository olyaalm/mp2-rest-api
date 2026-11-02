from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Status and version returned by the health endpoint."""

    status: str
    version: str


class DatasetInfo(BaseModel):
    """Metadata returned after a dataset is uploaded."""

    id: int
    filename: str
    rows: int
    columns: int
    column_names: list[str]


class ValidationSettings(BaseModel):
    """Column requirements used before cleaning a dataset."""

    # These lists tell validation which columns must exist and be numeric.
    required_columns: list[str] = Field(default_factory=list)
    numeric_columns: list[str] = Field(default_factory=list)


class MissingSettings(BaseModel):
    """Control whether missing-value rows or columns are removed."""

    # Rows with missing values are removed by default.
    enabled: bool = True
    axis: str = "rows"


class OutlierSettings(BaseModel):
    """Choose which numeric columns are checked for outliers."""

    # Outlier removal stays off unless the request enables it.
    enabled: bool = False
    columns: list[str] = Field(default_factory=list)
    method: str = "iqr"
    threshold: float = 1.5


class ProcessingSettings(BaseModel):
    """Settings for duplicate, missing-value, and outlier cleaning."""

    remove_duplicates: bool = True
    missing: MissingSettings = Field(default_factory=MissingSettings)
    outliers: OutlierSettings = Field(default_factory=OutlierSettings)


class ProcessConfig(BaseModel):
    """Complete request configuration for validation and processing."""

    # Each request gets fresh nested settings with predictable defaults.
    validation: ValidationSettings = Field(default_factory=ValidationSettings)
    processing: ProcessingSettings = Field(default_factory=ProcessingSettings)


class ProcessingReport(BaseModel):
    """Summarize validation removals and the later cleaning operations."""

    id: int
    validation_rows_removed: int
    cleaning_report: dict[str, int]