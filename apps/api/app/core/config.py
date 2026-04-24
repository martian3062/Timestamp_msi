from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="MSI_")

    environment: str = "local"
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://127.0.0.1:3000",
            "http://localhost:3000",
        ],
    )

    vm_user: str = "pardeep"
    vm_host: str = "34.55.157.128"
    vm_key: Path = Field(default_factory=lambda: Path.home() / ".ssh" / "evolet_rsa")
    vm_project_root: str = (
        "/home/pardeep/pathology310_projects/single_slide_morphology/"
        "project_1_slideflow_msi_tcga_crc"
    )
    vm_jupyter_port: int = 8888
    local_jupyter_port: int = 8888
    hf_token: str | None = None
    zerve_api_key: str | None = None
    firecrawl_api_key: str | None = None
    tinyfish_api_key: str | None = None

    @property
    def allowed_browse_roots(self) -> list[str]:
        root = self.vm_project_root.rstrip("/")
        return [
            root,
            f"{root}/annotations",
            f"{root}/scripts",
            f"{root}/slideflow_project",
            f"{root}/slideflow_project/data",
            f"{root}/slideflow_project/data/slides",
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
