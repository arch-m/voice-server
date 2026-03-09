#!/usr/bin/env python3
"""Gateway OCR unificado para proveedores internos."""

from __future__ import annotations

import json

import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from apps.ocr_gateway.config import DEEPSEEK_URL, GLM_URL, HOST, PORT, TIMEOUT
from packages.ocr_common.schemas import GatewayHealthResponse, GatewayProviderHealth, OcrProvider

app = FastAPI(
    title="OCR Gateway API",
    description="Gateway HTTP para proveedores OCR internos",
    version="0.1.0",
)


def _provider_base_url(provider: OcrProvider) -> str:
    if provider == OcrProvider.DEEPSEEK:
        return DEEPSEEK_URL
    return GLM_URL


@app.get("/health", response_model=GatewayHealthResponse)
async def health_check():
    providers = {}
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        for provider in OcrProvider:
            url = _provider_base_url(provider) + "/health"
            try:
                response = await client.get(url)
                detail = None
                if response.status_code >= 400:
                    detail = f"HTTP {response.status_code}"
                providers[provider.value] = GatewayProviderHealth(
                    reachable=response.status_code < 400,
                    detail=detail,
                )
            except Exception as exc:
                providers[provider.value] = GatewayProviderHealth(
                    reachable=False,
                    detail=str(exc),
                )

    return GatewayHealthResponse(status="ok", providers=providers)


@app.post("/ocr")
async def ocr(
    file: UploadFile = File(...),
    provider: OcrProvider = Form(...),
    mode: str = Form("markdown"),
    prompt: str = Form(""),
    save_results: bool = Form(False),
):
    filename = file.filename or "upload.bin"
    content = await file.read()
    files = {
        "file": (
            filename,
            content,
            file.content_type or "application/octet-stream",
        )
    }
    data = {
        "mode": mode,
        "prompt": prompt,
        "save_results": json.dumps(save_results),
    }
    url = _provider_base_url(provider) + "/ocr"

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            response = await client.post(url, data=data, files=files)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Gateway OCR fallo: {exc}")

    try:
        payload = response.json()
    except Exception:
        raise HTTPException(status_code=502, detail="Respuesta invalida del proveedor OCR")

    return JSONResponse(status_code=response.status_code, content=payload)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT)
