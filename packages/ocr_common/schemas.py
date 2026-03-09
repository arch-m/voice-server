"""Shared OCR API schemas."""

from enum import Enum

from pydantic import BaseModel


class OcrProvider(str, Enum):
    DEEPSEEK = "deepseek"
    GLM = "glm"


class OcrHealthResponse(BaseModel):
    status: str
    loaded: bool
    model: str
    device: str | None
    dtype: str | None


class OcrResponse(BaseModel):
    text: str
    mode: str
    prompt: str
    model: str
    output_dir: str | None = None


class GatewayProviderHealth(BaseModel):
    reachable: bool
    detail: str | None = None


class GatewayHealthResponse(BaseModel):
    status: str
    providers: dict[str, GatewayProviderHealth]
