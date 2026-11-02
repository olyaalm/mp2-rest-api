from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    version: str


class DatasetInfo(BaseModel):
    id: int
    filename: str
    rows: int
    columns: int
    column_names: list[str]


class ValidationSettings(BaseModel):
    # These lists tell validation which columns must exist and which must be numeric.
    required_columns: list[str] = Field(default_factory=list)
    numeric_columns: list[str] = Field(default_factory=list)


class MissingSettings(BaseModel):
    # By default, remove rows containing missing values.
    enabled: bool = True
    axis: str = "rows"


class OutlierSettings(BaseModel):
    # Outlier removal is off unless the request explicitly enables it.
    enabled: bool = False
    columns: list[str] = Field(default_factory=list)
    method: str = "iqr"
    threshold: float = 1.5


class ProcessingSettings(BaseModel):
    # These defaults apply duplicate, missing-value, and optional outlier steps.
    remove_duplicates: bool = True
    missing: MissingSettings = Field(default_factory=MissingSettings)
    outliers: OutlierSettings = Field(default_factory=OutlierSettings)


class ProcessConfig(BaseModel):
    # Nested settings are converted to the dictionary format expected by MP1.
    validation: ValidationSettings = Field(default_factory=ValidationSettings)
    processing: ProcessingSettings = Field(default_factory=ProcessingSettings)


class ProcessingReport(BaseModel):
    # Report validation separately from the later cleaning steps.
    id: int
    validation_rows_removed: int
    cleaning_report: dict[str, int]