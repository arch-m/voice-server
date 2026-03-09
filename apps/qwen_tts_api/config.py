"""Configuración para las apps Qwen3 TTS."""

from pathlib import Path
from typing import Any

from pydantic import Field, field_validator

from packages.platform_common.env import resolve_repo_path
from packages.platform_common.settings import RuntimePathsSettings


class Settings(RuntimePathsSettings):
    qwen_tts_model: Path | None = Field(default=None, validation_alias="QWEN_TTS_MODEL")
    qwen_tts_voice_clone_model: Path | None = Field(
        default=None,
        validation_alias="QWEN_TTS_VOICE_CLONE_MODEL",
    )
    qwen_device: str = Field(default="cuda:0", validation_alias="QWEN_DEVICE")
    qwen_dtype: str = Field(default="bfloat16", validation_alias="QWEN_DTYPE")
    qwen_default_language: str = Field(default="Spanish", validation_alias="QWEN_DEFAULT_LANGUAGE")
    qwen_default_speaker: str = Field(default="Vivian", validation_alias="QWEN_DEFAULT_SPEAKER")
    qwen_tts_sample_rate: int = Field(default=24000, validation_alias="QWEN_TTS_SAMPLE_RATE")
    qwen_voice_clone_enabled: bool = Field(default=True, validation_alias="QWEN_VOICE_CLONE_ENABLED")
    qwen_voice_clone_xvector_only: bool = Field(
        default=True,
        validation_alias="QWEN_VOICE_CLONE_XVECTOR_ONLY",
    )
    qwen_voice_clone_speaker_name: str = Field(
        default="MyVoice",
        validation_alias="QWEN_VOICE_CLONE_SPEAKER_NAME",
    )
    qwen_voice_clone_ref_audio: Path | None = Field(
        default=None,
        validation_alias="QWEN_VOICE_CLONE_REF_AUDIO",
    )
    qwen_voice_clone_ref_text: str = Field(default="", validation_alias="QWEN_VOICE_CLONE_REF_TEXT")
    qwen_voice_clone_service_url: str = Field(
        default="http://localhost:8004",
        validation_alias="QWEN_VOICE_CLONE_SERVICE_URL",
    )
    qwen_host: str = Field(default="0.0.0.0", validation_alias="QWEN_HOST")
    qwen_tts_port: int = Field(default=8002, validation_alias="QWEN_TTS_PORT")
    qwen_tts_clone_port: int = Field(default=8004, validation_alias="QWEN_TTS_CLONE_PORT")
    qwen_voice_reload: bool = Field(default=True, validation_alias="QWEN_VOICE_RELOAD")

    @field_validator(
        "qwen_tts_model",
        "qwen_tts_voice_clone_model",
        "qwen_voice_clone_ref_audio",
        mode="before",
    )
    @classmethod
    def _resolve_paths(cls, value: Any) -> Any:
        return resolve_repo_path(value)

    def model_post_init(self, __context: Any) -> None:
        if self.qwen_tts_model is None:
            self.qwen_tts_model = self.models_path("qwen-tts-customvoice")
        if self.qwen_tts_voice_clone_model is None:
            self.qwen_tts_voice_clone_model = self.models_path("qwen-tts-model")
        if self.qwen_voice_clone_ref_audio is None:
            self.qwen_voice_clone_ref_audio = self.media_path("mi-voz.wav")


settings = Settings()

TTS_MODEL = str(settings.qwen_tts_model)
TTS_VOICE_CLONE_MODEL = str(settings.qwen_tts_voice_clone_model)
DEVICE = settings.qwen_device
DTYPE = settings.qwen_dtype
DEFAULT_LANGUAGE = settings.qwen_default_language
DEFAULT_SPEAKER = settings.qwen_default_speaker
TTS_SAMPLE_RATE = settings.qwen_tts_sample_rate
VOICE_CLONE_ENABLED = settings.qwen_voice_clone_enabled
VOICE_CLONE_XVECTOR_ONLY_DEFAULT = settings.qwen_voice_clone_xvector_only
VOICE_CLONE_SPEAKER_NAME = settings.qwen_voice_clone_speaker_name
VOICE_CLONE_REF_AUDIO = str(settings.qwen_voice_clone_ref_audio)
VOICE_CLONE_REF_TEXT = settings.qwen_voice_clone_ref_text
VOICE_CLONE_SERVICE_URL = settings.qwen_voice_clone_service_url
HOST = settings.qwen_host
PORT = settings.qwen_tts_port
TTS_CLONE_PORT = settings.qwen_tts_clone_port
RELOAD = settings.qwen_voice_reload
