from fastapi import APIRouter

from app.models.cohort import CohortValidationRequest, CohortValidationResponse
from app.services.cohort import validate_cohort

router = APIRouter()


@router.post("/validate", response_model=CohortValidationResponse)
def validate(request: CohortValidationRequest) -> CohortValidationResponse:
    return validate_cohort(request)

