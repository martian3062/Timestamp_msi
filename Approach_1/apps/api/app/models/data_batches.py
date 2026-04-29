from pydantic import BaseModel, Field


class GdcBatchStartRequest(BaseModel):
    limit: int = Field(default=10, ge=1, le=25)
    prefer_dx: bool = True


class DataBatchActionResponse(BaseModel):
    ok: bool = True
    action: str
    stdout: str = ""
    stderr: str = ""
