from fastapi import APIRouter

from app.core.config import get_settings
from app.models.integrations import IntegrationStatus, IntegrationsStatusResponse

router = APIRouter()


@router.get("/status", response_model=IntegrationsStatusResponse)
def status() -> IntegrationsStatusResponse:
    settings = get_settings()
    return IntegrationsStatusResponse(
        integrations=[
            IntegrationStatus(
                name="Hugging Face",
                env_var="MSI_HF_TOKEN",
                configured=bool(settings.hf_token),
                use="Access gated HF pathology models and feature extractors.",
            ),
            IntegrationStatus(
                name="Zerve AI",
                env_var="MSI_ZERVE_API_KEY",
                configured=bool(settings.zerve_api_key),
                use="Optional experiment notebook/job orchestration bridge.",
            ),
            IntegrationStatus(
                name="Firecrawl",
                env_var="MSI_FIRECRAWL_API_KEY",
                configured=bool(settings.firecrawl_api_key),
                use="Optional research-source crawling and metadata extraction.",
            ),
            IntegrationStatus(
                name="Tinyfish",
                env_var="MSI_TINYFISH_API_KEY",
                configured=bool(settings.tinyfish_api_key),
                use="Optional browser/API automation for external data-source checks.",
            ),
        ]
    )
