#!/usr/bin/env python3
"""Servidor HTTP para Qwen3-ASR."""
import io
import subprocess

import soundfile as sf
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel

from apps.qwen_asr_api.config import ASR_HOST, ASR_MODEL, ASR_PORT, DEFAULT_LANGUAGE, DEVICE, DTYPE

app = FastAPI(title="Qwen3-ASR Server")

model = None


class ASRResponse(BaseModel):
    text: str
    language: str


def _decode_audio(content: bytes):
    """Decode audio bytes, falling back to ffmpeg for browser formats like webm/mp4."""
    try:
        audio, sample_rate = sf.read(io.BytesIO(content))
    except RuntimeError:
        proc = subprocess.run(
            [
                "ffmpeg",
                "-nostdin",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                "pipe:0",
                "-f",
                "wav",
                "-ac",
                "1",
                "pipe:1",
            ],
            input=content,
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0 or not proc.stdout:
            detail = proc.stderr.decode("utf-8", errors="ignore").strip() or "Formato de audio no soportado"
            raise HTTPException(status_code=400, detail=detail)
        audio, sample_rate = sf.read(io.BytesIO(proc.stdout))

    if len(audio.shape) > 1:
        audio = audio.mean(axis=1)

    return audio, sample_rate


def _transcribe_audio(content: bytes, language: str | None) -> ASRResponse:
    """Transcribe audio bytes with the loaded Qwen ASR model."""
    if model is None:
        raise HTTPException(503, "Modelo no cargado")

    try:
        audio, sample_rate = _decode_audio(content)
        requested_language = language or DEFAULT_LANGUAGE
        results = model.transcribe(audio=(audio, sample_rate), language=requested_language)

        if results:
            return ASRResponse(
                text=results[0].text,
                language=results[0].language or requested_language,
            )

        return ASRResponse(text="", language=requested_language)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")


@app.on_event("startup")
async def load_model():
    global model
    import torch
    from qwen_asr import Qwen3ASRModel

    dtype_map = {
        "float32": torch.float32,
        "float16": torch.float16,
        "bfloat16": torch.bfloat16,
    }

    print(f"Cargando modelo ASR desde {ASR_MODEL}...")
    model = Qwen3ASRModel.from_pretrained(
        ASR_MODEL,
        device_map=DEVICE,
        dtype=dtype_map.get(DTYPE, torch.bfloat16),
    )
    print("Modelo ASR cargado")

@app.get("/health")
async def health():
    return {"status": "ok", "asr_loaded": model is not None}


@app.post("/asr", response_model=ASRResponse)
async def transcribe(
    file: UploadFile = File(...),
    language: str = Form(DEFAULT_LANGUAGE)
):
    """Transcribe audio WAV a texto"""
    content = await file.read()
    return _transcribe_audio(content, language)


@app.post("/v1/audio/transcriptions")
async def openai_transcribe(
    file: UploadFile = File(...),
    model_name: str = Form("", alias="model"),
    language: str | None = Form(None),
    prompt: str | None = Form(None),
    response_format: str = Form("json"),
    temperature: float | None = Form(None),
):
    """OpenAI-compatible transcription endpoint for Open WebUI."""
    del model_name, prompt, temperature

    content = await file.read()
    result = _transcribe_audio(content, language)

    if response_format == "text":
        return PlainTextResponse(result.text)
    if response_format in {"json", "verbose_json"}:
        return JSONResponse({"text": result.text, "language": result.language})

    raise HTTPException(status_code=400, detail=f"response_format no soportado: {response_format}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=ASR_HOST, port=ASR_PORT)
