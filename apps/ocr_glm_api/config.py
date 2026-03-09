"""Configuración para la app GLM-OCR."""

from pydantic import Field

from packages.ocr_common.settings import OcrDefaultsSettings


class Settings(OcrDefaultsSettings):
    glm_ocr_model: str = Field(default="zai-org/GLM-OCR", validation_alias="GLM_OCR_MODEL")
    glm_ocr_device: str = Field(default="auto", validation_alias="GLM_OCR_DEVICE")
    glm_ocr_dtype: str | None = Field(default=None, validation_alias="GLM_OCR_DTYPE")
    glm_ocr_attn: str | None = Field(default=None, validation_alias="GLM_OCR_ATTN")
    glm_ocr_mode: str | None = Field(default=None, validation_alias="GLM_OCR_MODE")
    glm_ocr_base_size: int | None = Field(default=None, validation_alias="GLM_OCR_BASE_SIZE")
    glm_ocr_image_size: int | None = Field(default=None, validation_alias="GLM_OCR_IMAGE_SIZE")
    glm_ocr_crop_mode: str | None = Field(default=None, validation_alias="GLM_OCR_CROP_MODE")
    glm_ocr_max_new_tokens: int | None = Field(
        default=None,
        validation_alias="GLM_OCR_MAX_NEW_TOKENS",
    )
    glm_ocr_host: str | None = Field(default=None, validation_alias="GLM_OCR_HOST")
    glm_ocr_port: int = Field(default=8011, validation_alias="GLM_OCR_PORT")

    def model_post_init(self, __context) -> None:
        if self.glm_ocr_mode is None:
            self.glm_ocr_mode = self.ocr_default_mode
        if self.glm_ocr_base_size is None:
            self.glm_ocr_base_size = self.ocr_default_base_size
        if self.glm_ocr_image_size is None:
            self.glm_ocr_image_size = self.ocr_default_image_size
        if self.glm_ocr_crop_mode is None:
            self.glm_ocr_crop_mode = self.ocr_default_crop_mode
        if self.glm_ocr_max_new_tokens is None:
            self.glm_ocr_max_new_tokens = self.ocr_default_max_new_tokens
        if self.glm_ocr_host is None:
            self.glm_ocr_host = self.ocr_host


settings = Settings()

MODEL_ID = settings.glm_ocr_model
DEVICE = settings.glm_ocr_device
DTYPE = settings.glm_ocr_dtype
ATTN = settings.glm_ocr_attn
DEFAULT_MODE = settings.glm_ocr_mode
DEFAULT_BASE_SIZE = settings.glm_ocr_base_size
DEFAULT_IMAGE_SIZE = settings.glm_ocr_image_size
DEFAULT_CROP_MODE = settings.glm_ocr_crop_mode
DEFAULT_MAX_NEW_TOKENS = settings.glm_ocr_max_new_tokens
HOST = settings.glm_ocr_host
PORT = settings.glm_ocr_port
