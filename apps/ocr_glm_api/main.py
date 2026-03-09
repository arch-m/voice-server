#!/usr/bin/env python3
"""Servidor HTTP para GLM-OCR."""

import tempfile
import threading
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from packages.ocr_common.schemas import OcrHealthResponse, OcrResponse
from packages.ocr_glm.model import (
    OcrError,
    cleanup_output_dir,
    infer_image,
    load_model,
    resolve_prompt,
)
from apps.ocr_glm_api.config import (
    ATTN,
    DEFAULT_BASE_SIZE,
    DEFAULT_CROP_MODE,
    DEFAULT_IMAGE_SIZE,
    DEFAULT_MAX_NEW_TOKENS,
    DEFAULT_MODE,
    DEVICE,
    DTYPE,
    HOST,
    MODEL_ID,
    PORT,
)

app = FastAPI(
    title="GLM OCR API",
    description="OCR para imagenes usando GLM-OCR",
    version="0.1.0",
)

_model = None
_processor = None
_device = None
_dtype = None
_lock = threading.Lock()


def load_models_sync():
    global _model, _processor, _device, _dtype

    try:
        _model, _processor, _device, _dtype = load_model(
            MODEL_ID,
            device=DEVICE,
            dtype_name=DTYPE,
            attn_impl=ATTN,
        )
    except Exception as exc:
        print(f"Error cargando modelo OCR: {exc}")
        _model = None
        _processor = None
        _device = None
        _dtype = None


@app.on_event("startup")
async def load_models():
    # Avoid blocking app startup while model weights initialize.
    thread = threading.Thread(target=load_models_sync, daemon=True)
    thread.start()


@app.get("/health", response_model=OcrHealthResponse)
async def health_check():
    return OcrHealthResponse(
        status="ok",
        loaded=_model is not None,
        model=MODEL_ID,
        device=_device,
        dtype=str(_dtype) if _dtype else None,
    )


@app.post("/ocr", response_model=OcrResponse)
async def ocr(
    file: UploadFile = File(...),
    mode: str = Form(DEFAULT_MODE),
    prompt: str = Form(""),
    base_size: int = Form(DEFAULT_BASE_SIZE),
    image_size: int = Form(DEFAULT_IMAGE_SIZE),
    crop_mode: str = Form(DEFAULT_CROP_MODE),
    max_new_tokens: int = Form(DEFAULT_MAX_NEW_TOKENS),
    save_results: bool = Form(False),
):
    if _model is None or _processor is None:
        raise HTTPException(status_code=503, detail="Modelo OCR no disponible")

    if not file.filename:
        raise HTTPException(status_code=400, detail="Archivo requerido")

    suffix = Path(file.filename).suffix or ".png"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        prompt_text = resolve_prompt(mode, prompt.strip() or None)
        with _lock:
            text, output_dir, _ = infer_image(
                _model,
                _processor,
                image_path=tmp_path,
                prompt=prompt_text,
                base_size=base_size,
                image_size=image_size,
                crop_mode=crop_mode,
                save_results=save_results,
                max_new_tokens=max_new_tokens,
            )

        if not save_results:
            cleanup_output_dir(output_dir, keep=False)
            output_dir = None

        return OcrResponse(
            text=text,
            mode=mode,
            prompt=prompt_text,
            model=MODEL_ID,
            output_dir=output_dir,
        )
    except OcrError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        if tmp_path:
            try:
                Path(tmp_path).unlink()
            except OSError:
                pass


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT)
