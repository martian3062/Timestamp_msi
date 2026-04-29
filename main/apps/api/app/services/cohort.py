from app.models.cohort import (
    CohortValidationRequest,
    CohortValidationResponse,
    FieldMapping,
    ParsedTableSummary,
    UploadedTextFile,
)

TableRow = dict[str, str]

ANNOTATION_REQUIRED = ["patient", "slide", "label", "fold"]
MANIFEST_REQUIRED = ["id", "filename"]


def parse_delimited(text: str) -> tuple[list[TableRow], list[str]]:
    rows: list[list[str]] = []
    field = ""
    row: list[str] = []
    quoted = False
    index = 0

    while index < len(text):
        char = text[index]
        next_char = text[index + 1] if index + 1 < len(text) else ""

        if char == '"' and quoted and next_char == '"':
            field += '"'
            index += 2
            continue

        if char == '"':
            quoted = not quoted
            index += 1
            continue

        if not quoted and char in {",", "\t"}:
            row.append(field.strip())
            field = ""
            index += 1
            continue

        if not quoted and char in {"\n", "\r"}:
            if char == "\r" and next_char == "\n":
                index += 1
            row.append(field.strip())
            if any(cell for cell in row):
                rows.append(row)
            row = []
            field = ""
            index += 1
            continue

        field += char
        index += 1

    row.append(field.strip())
    if any(cell for cell in row):
        rows.append(row)

    if not rows:
        return [], []

    columns = [column.strip() for column in rows[0]]
    parsed_rows = []
    for cells in rows[1:]:
        parsed_rows.append(
            {
                column: cells[index].strip() if index < len(cells) else ""
                for index, column in enumerate(columns)
            }
        )

    return parsed_rows, columns


def normalize_column(column: str) -> str:
    return "".join(character for character in column.lower() if character.isalnum())


def find_column(columns: list[str], candidates: list[str]) -> str | None:
    normalized_candidates = [normalize_column(candidate) for candidate in candidates]

    for column in columns:
        normalized_column = normalize_column(column)
        if any(candidate in normalized_column for candidate in normalized_candidates):
            return column

    return None


def count_by(rows: list[TableRow], column: str | None) -> dict[str, int]:
    if not column:
        return {}

    counts: dict[str, int] = {}
    for row in rows:
        value = row.get(column, "").strip() or "Missing"
        counts[value] = counts.get(value, 0) + 1
    return counts


def annotation_mapping(columns: list[str]) -> FieldMapping:
    return FieldMapping(
        patient=find_column(columns, ["patient", "case", "submitter"]),
        slide=find_column(columns, ["slide", "filename", "file", "image"]),
        label=find_column(columns, ["msi", "label", "class", "status"]),
        fold=find_column(columns, ["fold", "split"]),
    )


def manifest_mapping(columns: list[str]) -> FieldMapping:
    return FieldMapping(
        id=find_column(columns, ["id", "uuid", "fileid"]),
        filename=find_column(columns, ["filename", "file", "name"]),
    )


def missing_fields(mapping: FieldMapping, required: list[str]) -> list[str]:
    return [field for field in required if getattr(mapping, field) is None]


def summarize_annotations(file: UploadedTextFile) -> tuple[ParsedTableSummary, dict[str, int], dict[str, int]]:
    rows, columns = parse_delimited(file.contents)
    mapping = annotation_mapping(columns)

    return (
        ParsedTableSummary(
            name=file.name,
            rows=len(rows),
            columns=columns,
            mapping=mapping,
            missing_required=missing_fields(mapping, ANNOTATION_REQUIRED),
        ),
        count_by(rows, mapping.label),
        count_by(rows, mapping.fold),
    )


def summarize_manifest(file: UploadedTextFile) -> ParsedTableSummary:
    rows, columns = parse_delimited(file.contents)
    mapping = manifest_mapping(columns)

    return ParsedTableSummary(
        name=file.name,
        rows=len(rows),
        columns=columns,
        mapping=mapping,
        missing_required=missing_fields(mapping, MANIFEST_REQUIRED),
    )


def validate_cohort(request: CohortValidationRequest) -> CohortValidationResponse:
    annotation_summary = None
    manifest_summary = None
    label_counts: dict[str, int] = {}
    fold_counts: dict[str, int] = {}

    if request.annotations:
        annotation_summary, label_counts, fold_counts = summarize_annotations(
            request.annotations
        )

    if request.manifest:
        manifest_summary = summarize_manifest(request.manifest)

    ready = bool(
        annotation_summary
        and manifest_summary
        and annotation_summary.rows > 0
        and manifest_summary.rows > 0
        and not annotation_summary.missing_required
        and not manifest_summary.missing_required
    )

    return CohortValidationResponse(
        annotations=annotation_summary,
        manifest=manifest_summary,
        label_counts=label_counts,
        fold_counts=fold_counts,
        ready_for_vm=ready,
    )
