from pydantic import BaseModel, Field


class UploadedTextFile(BaseModel):
    name: str
    contents: str


class FieldMapping(BaseModel):
    patient: str | None = None
    slide: str | None = None
    label: str | None = None
    fold: str | None = None
    id: str | None = None
    filename: str | None = None


class ParsedTableSummary(BaseModel):
    name: str
    rows: int
    columns: list[str]
    mapping: FieldMapping
    missing_required: list[str] = Field(default_factory=list)


class CohortValidationRequest(BaseModel):
    annotations: UploadedTextFile | None = None
    manifest: UploadedTextFile | None = None


class CohortValidationResponse(BaseModel):
    annotations: ParsedTableSummary | None = None
    manifest: ParsedTableSummary | None = None
    label_counts: dict[str, int] = Field(default_factory=dict)
    fold_counts: dict[str, int] = Field(default_factory=dict)
    ready_for_vm: bool = False

