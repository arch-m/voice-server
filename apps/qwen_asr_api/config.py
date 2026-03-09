"""Configuración para la app Qwen3 ASR."""

from pathlib import Path
from typing import Any

from pydantic import Field, field_validator

from packages.platform_common.env import resolve_repo_path
from packages.platform_common.settings import RuntimePathsSettings


class Settings(RuntimePathsSettings):
    qwen_asr_model: Path | None = Field(default=None, validation_alias="QWEN_ASR_MODEL")
    qwen_device: str = Field(default="cuda:0", validation_alias="QWEN_DEVICE")
    qwen_dtype: str = Field(default="bfloat16", validation_alias="QWEN_DTYPE")
    qwen_default_language: str = Field(default="Spanish", validation_alias="QWEN_DEFAULT_LANGUAGE")
    qwen_asr_host: str = Field(default="0.0.0.0", validation_alias="QWEN_ASR_HOST")
    qwen_asr_port: int = Field(default=8003, validation_alias="QWEN_ASR_PORT")

    @field_validator("qwen_asr_model", mode="before")
    @classmethod
    def _resolve_paths(cls, value: Any) -> Any:
        return resolve_repo_path(value)

    def model_post_init(self, __context: Any) -> None:
        if self.qwen_asr_model is None:
            self.qwen_asr_model = self.models_path("qwen-asr-model")


settings = Settings()

ASR_MODEL = str(settings.qwen_asr_model)
DEVICE = settings.qwen_device
DTYPE = settings.qwen_dtype
DEFAULT_LANGUAGE = settings.qwen_default_language
ASR_HOST = settings.qwen_asr_host
ASR_PORT = settings.qwen_asr_port
