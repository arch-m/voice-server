import os


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


TTS_MODEL = "./qwen-tts-customvoice"
TTS_VOICE_CLONE_MODEL = "./qwen-tts-model"
ASR_MODEL = "./qwen-asr-model"

DEVICE = "cuda:0"
DTYPE = "bfloat16"

DEFAULT_LANGUAGE = "Spanish"
DEFAULT_SPEAKER = "Vivian"

TTS_SAMPLE_RATE = 24000  # Hz TTS
ASR_SAMPLE_RATE = 16000  # Hz ASR

VOICE_CLONE_ENABLED = True
VOICE_CLONE_XVECTOR_ONLY_DEFAULT = True
VOICE_CLONE_SPEAKER_NAME = "MyVoice"
VOICE_CLONE_REF_AUDIO = "./tools/mi-voz.wav"
VOICE_CLONE_REF_TEXT = ""
VOICE_CLONE_SERVICE_URL = "http://localhost:8004"

HOST = "0.0.0.0"
PORT = 8002
TTS_CLONE_PORT = 8004
RELOAD = _env_bool("QWEN_VOICE_RELOAD", True)
