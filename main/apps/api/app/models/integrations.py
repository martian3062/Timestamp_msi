from pydantic import BaseModel


class IntegrationStatus(BaseModel):
    name: str
    env_var: str
    configured: bool
    use: str


class IntegrationsStatusResponse(BaseModel):
    ok: bool = True
    integrations: list[IntegrationStatus]
