"""Servidor FastAPI para Qwen3 TTS."""

import io
import json
import urllib.error
import urllib.request
from pathlib import Path

import soundfile as sf
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from apps.qwen_tts_api.config import (
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
    VOICE_CLONE_SPEAKER_NAME,
    VOICE_CLONE_SERVICE_URL,
    VOICE_CLONE_XVECTOR_ONLY_DEFAULT,
)

app = FastAPI(
    title="Qwen3 Voice API",
    description="TTS usando modelos Qwen3",
    version="1.0.0",
)

# Variables globales para los modelos (cargados al iniciar)
tts_model = None
tts_clone_model = None


class TTSRequest(BaseModel):
    """Request body para el endpoint TTS."""

    text: str
    language: str = DEFAULT_LANGUAGE
    speaker: str = DEFAULT_SPEAKER
    instruct: str = ""


class HealthResponse(BaseModel):
    """Response body para el endpoint health."""

    status: str
    tts_loaded: bool
    tts_clone_loaded: bool


class OpenAISpeechRequest(BaseModel):
    """Request body para el endpoint OpenAI-compatible de TTS."""

    model: str = ""
    input: str
    voice: str = DEFAULT_SPEAKER
    response_format: str = "mp3"
    speed: float = 1.0


def get_torch_dtype():
    """Convierte string de dtype a torch dtype."""
    import torch

    dtype_map = {
        "float32": torch.float32,
        "float16": torch.float16,
        "bfloat16": torch.bfloat16,
    }
    return dtype_map.get(DTYPE, torch.bfloat16)


def _normalize_speaker(speaker: str | None) -> str:
    if not speaker or not speaker.strip():
        return DEFAULT_SPEAKER
    return speaker.strip()


def _proxy_voice_clone(text: str, language: str) -> bytes:
    """Proxy a servicio de clonacion si está configurado."""
    if not VOICE_CLONE_SERVICE_URL:
        raise HTTPException(status_code=500, detail="VOICE_CLONE_SERVICE_URL no configurado")

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


def _generate_audio(text: str, language: str, speaker: str, instruct: str = ""):
    """Generate raw audio data with either the standard TTS model or voice cloning."""
    if tts_model is None:
        raise HTTPException(status_code=503, detail="Modelo TTS no disponible")

    if not text.strip():
        raise HTTPException(status_code=400, detail="El texto no puede estar vacío")

    speaker = _normalize_speaker(speaker)

    try:
        use_voice_clone = (
            VOICE_CLONE_ENABLED
            and speaker.strip().lower() == VOICE_CLONE_SPEAKER_NAME.lower()
        )

        if use_voice_clone:
            if VOICE_CLONE_SERVICE_URL:
                return _proxy_voice_clone(text, language), "wav"
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
            if not VOICE_CLONE_XVECTOR_ONLY_DEFAULT and not VOICE_CLONE_REF_TEXT.strip():
                raise HTTPException(
                    status_code=500,
                    detail="VOICE_CLONE_REF_TEXT es requerido cuando xvector-only es false",
                )

            audio_array, sample_rate = tts_clone_model.generate(
                text=text,
                language=language,
                ref_audio=VOICE_CLONE_REF_AUDIO,
                ref_text=VOICE_CLONE_REF_TEXT if VOICE_CLONE_REF_TEXT.strip() else None,
                x_vector_only_mode=VOICE_CLONE_XVECTOR_ONLY_DEFAULT,
            )
        else:
            audio_array, sample_rate = tts_model.generate(
                text=text,
                language=language,
                speaker=speaker,
                instruct=instruct if instruct else None,
            )

        return (audio_array, sample_rate or TTS_SAMPLE_RATE), "pcm"
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando audio: {str(e)}")


def _encode_audio(audio_array, sample_rate: int, response_format: str) -> tuple[bytes, str, str]:
    """Encode generated audio into the requested container/codec."""
    fmt = (response_format or "wav").strip().lower()
    buffer = io.BytesIO()

    if fmt in {"wav", "wave"}:
        sf.write(buffer, audio_array, sample_rate, format="WAV")
        media_type = "audio/wav"
        filename = "tts_output.wav"
    elif fmt in {"mp3", "mpeg"}:
        sf.write(buffer, audio_array, sample_rate, format="MP3", subtype="MPEG_LAYER_III")
        media_type = "audio/mpeg"
        filename = "tts_output.mp3"
    else:
        raise HTTPException(status_code=400, detail=f"response_format no soportado: {response_format}")

    buffer.seek(0)
    return buffer.read(), media_type, filename


@app.on_event("startup")
async def load_models():
    """Carga los modelos TTS al iniciar el servidor."""
    global tts_model, tts_clone_model

    print(f"Cargando modelo TTS: {TTS_MODEL}")
    try:
        from packages.qwen_tts_runtime import QwenTTS, QwenVoiceClone

        tts_model = QwenTTS(
            model_path=TTS_MODEL,
            device=DEVICE,
            dtype=get_torch_dtype(),
        )
        print("Modelo TTS cargado exitosamente")

        if VOICE_CLONE_ENABLED and TTS_VOICE_CLONE_MODEL and not VOICE_CLONE_SERVICE_URL:
            print(f"Cargando modelo TTS Voice Clone: {TTS_VOICE_CLONE_MODEL}")
            tts_clone_model = QwenVoiceClone(
                model_path=TTS_VOICE_CLONE_MODEL,
                device=DEVICE,
                dtype=get_torch_dtype(),
            )
            print("Modelo TTS Voice Clone cargado exitosamente")
    except Exception as e:
        print(f"Error cargando modelo TTS: {e}")

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Verifica el estado del servidor y los modelos."""
    return HealthResponse(
        status="ok",
        tts_loaded=tts_model is not None,
        tts_clone_loaded=tts_clone_model is not None,
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
    audio_result, kind = _generate_audio(
        text=request.text,
        language=request.language,
        speaker=request.speaker,
        instruct=request.instruct,
    )

    if kind == "wav":
        return Response(
            content=audio_result,
            media_type="audio/wav",
            headers={"Content-Disposition": "attachment; filename=tts_output.wav"},
        )

    audio_array, sample_rate = audio_result
    audio_bytes, media_type, filename = _encode_audio(audio_array, sample_rate, "wav")
    return Response(
        content=audio_bytes,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.post("/v1/audio/speech")
async def openai_text_to_speech(request: OpenAISpeechRequest):
    """OpenAI-compatible speech synthesis endpoint for Open WebUI."""
    requested_format = (request.response_format or "mp3").strip().lower()

    audio_result, kind = _generate_audio(
        text=request.input,
        language=DEFAULT_LANGUAGE,
        speaker=request.voice,
    )

    if kind == "wav":
        if requested_format in {"mp3", "mpeg"}:
            audio_array, sample_rate = sf.read(io.BytesIO(audio_result))
            audio_bytes, media_type, filename = _encode_audio(audio_array, sample_rate, "mp3")
        elif requested_format in {"wav", "wave"}:
            audio_bytes = audio_result
            media_type = "audio/wav"
            filename = "tts_output.wav"
        else:
            raise HTTPException(status_code=400, detail=f"response_format no soportado: {request.response_format}")
    else:
        audio_array, sample_rate = audio_result
        audio_bytes, media_type, filename = _encode_audio(
            audio_array,
            sample_rate,
            requested_format,
        )

    return Response(
        content=audio_bytes,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


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
        raise HTTPException(status_code=503, detail="Modelo TTS Voice Clone no disponible")

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

        # Generar audio con voice cloning
        audio_array, sample_rate = tts_clone_model.generate(
            text=text,
            language=language,
            ref_audio=ref_audio,
            ref_sr=ref_sr,
            ref_text=ref_text if ref_text.strip() else None,
            x_vector_only_mode=x_vector_only_mode,
        )

        # Convertir a WAV en memoria
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

    from apps.qwen_tts_api.config import HOST, PORT, RELOAD

    if RELOAD:
        uvicorn.run("apps.qwen_tts_api.main:app", host=HOST, port=PORT, reload=True)
    else:
        uvicorn.run(app, host=HOST, port=PORT)
