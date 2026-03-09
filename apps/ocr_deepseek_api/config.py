"""Configuración para la app DeepSeek OCR 2."""

from pathlib import Path
from typing import Any

from pydantic import Field, field_validator

from packages.ocr_common.settings import OcrDefaultsSettings
from packages.platform_common.env import resolve_repo_path


class Settings(OcrDefaultsSettings):
    deepseek_ocr2_model: Path | None = Field(default=None, validation_alias="DEEPSEEK_OCR2_MODEL")
    deepseek_ocr2_device: str = Field(default="auto", validation_alias="DEEPSEEK_OCR2_DEVICE")
    deepseek_ocr2_dtype: str | None = Field(default=None, validation_alias="DEEPSEEK_OCR2_DTYPE")
    deepseek_ocr2_attn: str | None = Field(default=None, validation_alias="DEEPSEEK_OCR2_ATTN")
    deepseek_ocr2_mode: str | None = Field(default=None, validation_alias="DEEPSEEK_OCR2_MODE")
    deepseek_ocr2_base_size: int | None = Field(default=None, validation_alias="DEEPSEEK_OCR2_BASE_SIZE")
    deepseek_ocr2_image_size: int | None = Field(default=None, validation_alias="DEEPSEEK_OCR2_IMAGE_SIZE")
    deepseek_ocr2_crop_mode: str | None = Field(default=None, validation_alias="DEEPSEEK_OCR2_CROP_MODE")
    deepseek_ocr2_host: str | None = Field(default=None, validation_alias="DEEPSEEK_OCR2_HOST")
    deepseek_ocr2_port: int = Field(default=8010, validation_alias="DEEPSEEK_OCR2_PORT")

    @field_validator("deepseek_ocr2_model", mode="before")
    @classmethod
    def _resolve_paths(cls, value: Any) -> Any:
        return resolve_repo_path(value)

    def model_post_init(self, __context: Any) -> None:
        if self.deepseek_ocr2_model is None:
            self.deepseek_ocr2_model = self.models_path("deepseek-ocr2")
        if self.deepseek_ocr2_mode is None:
            self.deepseek_ocr2_mode = self.ocr_default_mode
        if self.deepseek_ocr2_base_size is None:
            self.deepseek_ocr2_base_size = self.ocr_default_base_size
        if self.deepseek_ocr2_image_size is None:
            self.deepseek_ocr2_image_size = self.ocr_default_image_size
        if self.deepseek_ocr2_crop_mode is None:
            self.deepseek_ocr2_crop_mode = self.ocr_default_crop_mode
        if self.deepseek_ocr2_host is None:
            self.deepseek_ocr2_host = self.ocr_host


settings = Settings()

MODEL_ID = str(settings.deepseek_ocr2_model)
DEVICE = settings.deepseek_ocr2_device
DTYPE = settings.deepseek_ocr2_dtype
ATTN = settings.deepseek_ocr2_attn
DEFAULT_MODE = settings.deepseek_ocr2_mode
DEFAULT_BASE_SIZE = settings.deepseek_ocr2_base_size
DEFAULT_IMAGE_SIZE = settings.deepseek_ocr2_image_size
DEFAULT_CROP_MODE = settings.deepseek_ocr2_crop_mode
HOST = settings.deepseek_ocr2_host
PORT = settings.deepseek_ocr2_port
