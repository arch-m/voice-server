"""Configuración para el gateway OCR."""

from pydantic import Field

from packages.platform_common.settings import RepoSettings


class Settings(RepoSettings):
    ocr_gateway_host: str = Field(default="0.0.0.0", validation_alias="OCR_GATEWAY_HOST")
    ocr_gateway_port: int = Field(default=8012, validation_alias="OCR_GATEWAY_PORT")
    ocr_gateway_timeout: float = Field(default=180.0, validation_alias="OCR_GATEWAY_TIMEOUT")
    ocr_deepseek_url: str = Field(
        default="http://localhost:8010",
        validation_alias="OCR_DEEPSEEK_URL",
    )
    ocr_glm_url: str = Field(
        default="http://localhost:8011",
        validation_alias="OCR_GLM_URL",
    )


settings = Settings()

HOST = settings.ocr_gateway_host
PORT = settings.ocr_gateway_port
TIMEOUT = settings.ocr_gateway_timeout
DEEPSEEK_URL = settings.ocr_deepseek_url.rstrip("/")
GLM_URL = settings.ocr_glm_url.rstrip("/")
