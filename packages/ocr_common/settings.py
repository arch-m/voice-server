"""Shared OCR settings."""

from pydantic import Field

from packages.platform_common.settings import RuntimePathsSettings


class OcrDefaultsSettings(RuntimePathsSettings):
    """Common OCR defaults shared by provider apps."""

    ocr_host: str = Field(default="0.0.0.0", validation_alias="OCR_HOST")
    ocr_default_mode: str = Field(default="markdown", validation_alias="OCR_DEFAULT_MODE")
    ocr_default_base_size: int = Field(default=1024, validation_alias="OCR_DEFAULT_BASE_SIZE")
    ocr_default_image_size: int = Field(default=768, validation_alias="OCR_DEFAULT_IMAGE_SIZE")
    ocr_default_crop_mode: str = Field(default="true", validation_alias="OCR_DEFAULT_CROP_MODE")
    ocr_default_max_new_tokens: int = Field(
        default=8192,
        validation_alias="OCR_DEFAULT_MAX_NEW_TOKENS",
    )
