"""Servidor FastAPI para Qwen3 TTS y ASR."""

import io
import json
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np
import soundfile as sf
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from config import (
    ASR_MODEL,
    ASR_SAMPLE_RATE,
    DEFAULT_LANGUAGE,
    DEFAULT_SPEAKER,
    DEVICE,
    DTYPE,
    TTS_MODEL,
    TTS_SAMPLE_RATE,
    TTS_VOICE_CLONE_MODEL,
    VOICE_CLONE_ENABLED,
    VOICE_CLONE_REF_AUDIO,
    VOICE_CLONE_REF_TEXT,
    VOICE_CLONE_SERVICE_URL,
    VOICE_CLONE_SPEAKER_NAME,
    VOICE_CLONE_XVECTOR_ONLY_DEFAULT,
)

app = FastAPI(
    title="Qwen3 Voice API",
    description="TTS y ASR usando modelos Qwen3",
    version="1.0.0",
)

tts_model = None
tts_clone_model = None
asr_model = None


class TTSRequest(BaseModel):
    """Request body para el endpoint TTS."""

    text: str
    language: str = DEFAULT_LANGUAGE
    speaker: str = DEFAULT_SPEAKER
    instruct: str = ""


class ASRResponse(BaseModel):
    """Response body para el endpoint ASR."""

    text: str
    language: str


class HealthResponse(BaseModel):
    """Response body para el endpoint health."""

    status: str
    tts_loaded: bool
    tts_clone_loaded: bool
    asr_loaded: bool


def get_torch_dtype():
    """Convierte string de dtype a torch dtype."""
    import torch

    dtype_map = {
        "float32": torch.float32,
        "float16": torch.float16,
        "bfloat16": torch.bfloat16,
    }
    return dtype_map.get(DTYPE, torch.bfloat16)


def _proxy_voice_clone(text: str, language: str) -> bytes:
    """Proxy a servicio de clonacion si está configurado."""
    if not VOICE_CLONE_SERVICE_URL:
        raise HTTPException(
            status_code=500, detail="VOICE_CLONE_SERVICE_URL no configurado"
        )

    url = VOICE_CLONE_SERVICE_URL.rstrip("/") + "/tts"
    payload = json.dumps({"text": text, "language": language}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        detail = None
        try:
            body = e.read().decode("utf-8", errors="ignore")
            detail = json.loads(body).get("detail")
        except Exception:
            detail = None
        raise HTTPException(
            status_code=e.code,
            detail=detail or "Error en servicio de clonación",
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Proxy clonación falló: {e}")


@app.on_event("startup")
async def load_models():
    """Carga los modelos TTS y ASR al iniciar el servidor."""
    global tts_model, tts_clone_model, asr_model

    print(f"Cargando modelo TTS: {TTS_MODEL}")
    try:
        from qwen_models import QwenTTS, QwenVoiceClone

        tts_model = QwenTTS(
            model_path=TTS_MODEL,
            device=DEVICE,
            dtype=get_torch_dtype(),
        )
        print("Modelo TTS cargado exitosamente")

        if (
            VOICE_CLONE_ENABLED
            and TTS_VOICE_CLONE_MODEL
            and not VOICE_CLONE_SERVICE_URL
        ):
            print(f"Cargando modelo TTS Voice Clone: {TTS_VOICE_CLONE_MODEL}")
            tts_clone_model = QwenVoiceClone(
                model_path=TTS_VOICE_CLONE_MODEL,
                device=DEVICE,
                dtype=get_torch_dtype(),
            )
            print("Modelo TTS Voice Clone cargado exitosamente")
    except Exception as e:
        print(f"Error cargando modelo TTS: {e}")

    print(f"Cargando modelo ASR: {ASR_MODEL}")
    try:
        from qwen_models import QwenASR

        asr_model = QwenASR(
            model_path=ASR_MODEL,
            device=DEVICE,
            dtype=get_torch_dtype(),
        )
        print("Modelo ASR cargado exitosamente")
    except Exception as e:
        print(f"Error cargando modelo ASR: {e}")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Verifica el estado del servidor y los modelos."""
    return HealthResponse(
        status="ok",
        tts_loaded=tts_model is not None,
        tts_clone_loaded=tts_clone_model is not None,
        asr_loaded=asr_model is not None,
    )


@app.post("/tts")
async def text_to_speech(request: TTSRequest):
    """
    Convierte texto a audio WAV.

    Args:
        request: TTSRequest con text, language, speaker, instruct

    Returns:
        Audio WAV binario
    """
    if tts_model is None:
        raise HTTPException(status_code=503, detail="Modelo TTS no disponible")

    if not request.text.strip():
        raise HTTPException(status_code=400, detail="El texto no puede estar vacío")

    try:
        use_voice_clone = (
            VOICE_CLONE_ENABLED
            and request.speaker
            and request.speaker.strip().lower() == VOICE_CLONE_SPEAKER_NAME.lower()
        )

        if use_voice_clone:
            if VOICE_CLONE_SERVICE_URL:
                audio_bytes = _proxy_voice_clone(request.text, request.language)
                return Response(
                    content=audio_bytes,
                    media_type="audio/wav",
                    headers={
                        "Content-Disposition": "attachment; filename=tts_output.wav"
                    },
                )
            if tts_clone_model is None:
                raise HTTPException(
                    status_code=503,
                    detail="Modelo TTS Voice Clone no disponible",
                )
            if not VOICE_CLONE_REF_AUDIO or not Path(VOICE_CLONE_REF_AUDIO).exists():
                raise HTTPException(
                    status_code=500,
                    detail="Archivo de referencia para clonación no encontrado",
                )
            if (
                not VOICE_CLONE_XVECTOR_ONLY_DEFAULT
                and not VOICE_CLONE_REF_TEXT.strip()
            ):
                raise HTTPException(
                    status_code=500,
                    detail="VOICE_CLONE_REF_TEXT es requerido cuando xvector-only es false",
                )

            audio_array, sample_rate = tts_clone_model.generate(
                text=request.text,
                language=request.language,
                ref_audio=VOICE_CLONE_REF_AUDIO,
                ref_text=VOICE_CLONE_REF_TEXT if VOICE_CLONE_REF_TEXT.strip() else None,
                x_vector_only_mode=VOICE_CLONE_XVECTOR_ONLY_DEFAULT,
            )
        else:
            audio_array, sample_rate = tts_model.generate(
                text=request.text,
                language=request.language,
                speaker=request.speaker,
                instruct=request.instruct if request.instruct else None,
            )

        buffer = io.BytesIO()
        if not sample_rate:
            sample_rate = TTS_SAMPLE_RATE
        sf.write(buffer, audio_array, sample_rate, format="WAV")
        buffer.seek(0)

        return Response(
            content=buffer.read(),
            media_type="audio/wav",
            headers={"Content-Disposition": "attachment; filename=tts_output.wav"},
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando audio: {str(e)}")


@app.post("/tts/clone")
async def text_to_speech_clone(
    text: str = Form(...),
    file: UploadFile = File(...),
    language: str = Form(DEFAULT_LANGUAGE),
    ref_text: str = Form(""),
    x_vector_only_mode: bool = Form(VOICE_CLONE_XVECTOR_ONLY_DEFAULT),
):
    """
    Clona voz desde un audio de referencia y genera audio WAV.

    Args:
        text: Texto a sintetizar
        file: Audio WAV de referencia
        language: Idioma del texto
        ref_text: Transcripcion del audio de referencia (requerida si x_vector_only_mode=False)
        x_vector_only_mode: True => solo embedding de speaker, no requiere ref_text

    Returns:
        Audio WAV binario
    """
    if tts_clone_model is None:
        raise HTTPException(
            status_code=503, detail="Modelo TTS Voice Clone no disponible"
        )

    if not text.strip():
        raise HTTPException(status_code=400, detail="El texto no puede estar vacío")

    if not file.filename.lower().endswith((".wav", ".wave")):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos WAV")

    if not x_vector_only_mode and not ref_text.strip():
        raise HTTPException(
            status_code=400,
            detail="ref_text es requerido cuando x_vector_only_mode=False",
        )

    try:
        content = await file.read()
        buffer = io.BytesIO(content)
        ref_audio, ref_sr = sf.read(buffer)

        if len(ref_audio.shape) > 1:
            ref_audio = ref_audio.mean(axis=1)

        audio_array, sample_rate = tts_clone_model.generate(
            text=text,
            language=language,
            ref_audio=ref_audio,
            ref_sr=ref_sr,
            ref_text=ref_text if ref_text.strip() else None,
            x_vector_only_mode=x_vector_only_mode,
        )

        buffer = io.BytesIO()
        if not sample_rate:
            sample_rate = TTS_SAMPLE_RATE
        sf.write(buffer, audio_array, sample_rate, format="WAV")
        buffer.seek(0)

        return Response(
            content=buffer.read(),
            media_type="audio/wav",
            headers={
                "Content-Disposition": "attachment; filename=tts_clone_output.wav"
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando audio: {str(e)}")


@app.post("/asr", response_model=ASRResponse)
async def speech_to_text(
    file: UploadFile = File(...),
    language: str = Form(DEFAULT_LANGUAGE),
):
    """
    Convierte audio WAV a texto.

    Args:
        file: Archivo de audio WAV
        language: Idioma esperado del audio

    Returns:
        ASRResponse con el texto transcrito
    """
    if asr_model is None:
        raise HTTPException(status_code=503, detail="Modelo ASR no disponible")

    if not file.filename.lower().endswith((".wav", ".wave")):
        raise HTTPException(
            status_code=400,
            detail="Solo se aceptan archivos WAV",
        )

    try:
        content = await file.read()
        buffer = io.BytesIO(content)

        audio_array, sample_rate = sf.read(buffer)

        if sample_rate != ASR_SAMPLE_RATE:
            duration = len(audio_array) / sample_rate
            new_length = int(duration * ASR_SAMPLE_RATE)
            audio_array = np.interp(
                np.linspace(0, len(audio_array), new_length),
                np.arange(len(audio_array)),
                audio_array,
            )

        if len(audio_array.shape) > 1:
            audio_array = audio_array.mean(axis=1)

        result = asr_model.transcribe(
            audio=audio_array,
            language=language,
        )

        return ASRResponse(
            text=result["text"],
            language=language,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error transcribiendo audio: {str(e)}",
        )


if __name__ == "__main__":
    import uvicorn

    from config import HOST, PORT, RELOAD

    if RELOAD:
        uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
    else:
        uvicorn.run(app, host=HOST, port=PORT)
