"""Servidor FastAPI para Qwen3 TTS Voice Clone (Base)."""

import io
from pathlib import Path

import soundfile as sf
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from apps.qwen_tts_api.config import (
    DEFAULT_LANGUAGE,
    DEVICE,
    DTYPE,
    HOST,
    RELOAD,
    TTS_CLONE_PORT,
    TTS_SAMPLE_RATE,
    TTS_VOICE_CLONE_MODEL,
    VOICE_CLONE_REF_AUDIO,
    VOICE_CLONE_REF_TEXT,
    VOICE_CLONE_XVECTOR_ONLY_DEFAULT,
)

app = FastAPI(
    title="Qwen3 Voice Clone API",
    description="TTS Voice Clone usando modelo Base de Qwen3-TTS",
    version="1.0.0",
)

tts_clone_model = None


class TTSCloneRequest(BaseModel):
    """Request body para el endpoint TTS Clone."""

    text: str
    language: str = DEFAULT_LANGUAGE


class HealthResponse(BaseModel):
    """Response body para el endpoint health."""

    status: str
    tts_clone_loaded: bool


def get_torch_dtype():
    """Convierte string de dtype a torch dtype."""
    import torch

    dtype_map = {
        "float32": torch.float32,
        "float16": torch.float16,
        "bfloat16": torch.bfloat16,
    }
    return dtype_map.get(DTYPE, torch.bfloat16)


@app.on_event("startup")
async def load_model():
    """Carga el modelo TTS Base al iniciar el servidor."""
    global tts_clone_model

    print(f"Cargando modelo TTS Voice Clone: {TTS_VOICE_CLONE_MODEL}")
    try:
        from packages.qwen_tts_runtime import QwenVoiceClone

        tts_clone_model = QwenVoiceClone(
            model_path=TTS_VOICE_CLONE_MODEL,
            device=DEVICE,
            dtype=get_torch_dtype(),
        )
        print("Modelo TTS Voice Clone cargado exitosamente")
    except Exception as e:
        print(f"Error cargando modelo TTS Voice Clone: {e}")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Verifica el estado del servidor y el modelo."""
    return HealthResponse(
        status="ok",
        tts_clone_loaded=tts_clone_model is not None,
    )


@app.post("/tts")
async def text_to_speech_clone(request: TTSCloneRequest):
    """Clona voz desde un audio de referencia y genera audio WAV."""
    if tts_clone_model is None:
        raise HTTPException(status_code=503, detail="Modelo TTS Voice Clone no disponible")

    if not request.text.strip():
        raise HTTPException(status_code=400, detail="El texto no puede estar vacío")

    if not VOICE_CLONE_REF_AUDIO or not Path(VOICE_CLONE_REF_AUDIO).exists():
        raise HTTPException(
            status_code=500,
            detail="Archivo de referencia para clonación no encontrado",
        )

    if not VOICE_CLONE_XVECTOR_ONLY_DEFAULT and not VOICE_CLONE_REF_TEXT.strip():
        raise HTTPException(
            status_code=500,
            detail="VOICE_CLONE_REF_TEXT es requerido cuando xvector-only es false",
        )

    try:
        audio_array, sample_rate = tts_clone_model.generate(
            text=request.text,
            language=request.language,
            ref_audio=VOICE_CLONE_REF_AUDIO,
            ref_text=VOICE_CLONE_REF_TEXT if VOICE_CLONE_REF_TEXT.strip() else None,
            x_vector_only_mode=VOICE_CLONE_XVECTOR_ONLY_DEFAULT,
        )

        buffer = io.BytesIO()
        if not sample_rate:
            sample_rate = TTS_SAMPLE_RATE
        sf.write(buffer, audio_array, sample_rate, format="WAV")
        buffer.seek(0)

        return Response(
            content=buffer.read(),
            media_type="audio/wav",
            headers={"Content-Disposition": "attachment; filename=tts_clone_output.wav"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando audio: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    if RELOAD:
        uvicorn.run("apps.qwen_tts_api.tts_clone_server:app", host=HOST, port=TTS_CLONE_PORT, reload=True)
    else:
        uvicorn.run(app, host=HOST, port=TTS_CLONE_PORT)
