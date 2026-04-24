from typing import Literal

from pydantic import BaseModel


class VmActionResponse(BaseModel):
    ok: bool = True
    action: str
    stdout: str = ""
    stderr: str = ""


class VmFile(BaseModel):
    type: Literal["file", "directory", "other"]
    name: str
    size: int
    modified: str


class VmFilesResponse(VmActionResponse):
    path: str
    files: list[VmFile]


class FileUploadRequest(BaseModel):
    kind: Literal["annotations", "manifest"]
    contents: str

