#!/usr/bin/env python3
"""Servidor HTTP para Qwen3-ASR"""

import io

import numpy as np
import soundfile as sf
import torch
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

app = FastAPI(title="Qwen3-ASR Server")

MODEL_PATH = "/home/carat/models/qwen-asr-model"
model = None


class ASRResponse(BaseModel):
    text: str
    language: str


@app.on_event("startup")
async def load_model():
    global model
    from qwen_asr import Qwen3ASRModel

    print(f"Cargando modelo ASR desde {MODEL_PATH}...")
    model = Qwen3ASRModel.from_pretrained(
        MODEL_PATH, device_map="cuda:0", dtype=torch.bfloat16
    )
    print("Modelo ASR cargado")


@app.get("/health")
async def health():
    return {"status": "ok", "asr_loaded": model is not None}


@app.post("/asr", response_model=ASRResponse)
async def transcribe(file: UploadFile = File(...), language: str = Form("Spanish")):
    """Transcribe audio WAV a texto"""
    if model is None:
        raise HTTPException(503, "Modelo no cargado")

    try:
        content = await file.read()
        audio, sr = sf.read(io.BytesIO(content))

        # mono -> stereo
        if len(audio.shape) > 1:
            audio = audio.mean(axis=1)

        results = model.transcribe(audio=(audio, sr), language=language)

        if results:
            return ASRResponse(
                text=results[0].text, language=results[0].language or language
            )
        return ASRResponse(text="", language=language)
    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8003)
