# Local installation with `uv`

## Structure

The repo is split into two layers:

- `apps/`: HTTP services and executable entrypoints.
- `packages/`: reusable utilities, settings, and runtimes.

Active services:

| Service | App | Port | Environment |
|---|---|---:|---|
| Qwen TTS | `apps/qwen_tts_api` | 8002 | `apps/qwen_tts_api/.venv` |
| Qwen TTS Clone | `apps/qwen_tts_api` | 8004 | `apps/qwen_tts_api/.venv` |
| Qwen ASR | `apps/qwen_asr_api` | 8003 | `apps/qwen_asr_api/.venv` |
| DeepSeek OCR 2 | `apps/ocr_deepseek_api` | 8010 | `apps/ocr_deepseek_api/.venv` |
| GLM-OCR | `apps/ocr_glm_api` | 8011 | `apps/ocr_glm_api/.venv` |
| OCR Gateway | `apps/ocr_gateway` | 8012 | `apps/ocr_gateway/.venv` |

## Requirements

- Arch Linux
- `uv`
- `python3.11`
- NVIDIA GPU for the heavy models

Base installation:

```bash
sudo pacman -S uv
```

## Quick bootstrap

```bash
cd /path/to/repo
make sync-tts
make sync-asr
make sync-deepseek
make sync-ocr
make sync-ocr-gateway
```

Installers per service:

```bash
bash ./scripts/install/qwen-tts.sh
bash ./scripts/install/qwen-asr.sh
bash ./scripts/install/deepseek-ocr2.sh
bash ./scripts/install/glm-ocr.sh
bash ./scripts/install/ocr-gateway.sh
```

## Environment variables

Local configuration lives in `.env`. Use `.env.example` as a template.

Base variables:

- `MODELS_DIR`
- `MEDIA_DIR`

Qwen apps:

- `QWEN_TTS_MODEL`
- `QWEN_TTS_VOICE_CLONE_MODEL`
- `QWEN_ASR_MODEL`
- `QWEN_VOICE_CLONE_REF_AUDIO`
- `QWEN_TTS_PORT`
- `QWEN_TTS_CLONE_PORT`
- `QWEN_ASR_PORT`

OCR apps:

- `DEEPSEEK_OCR2_*`
- `GLM_OCR_*`
- `OCR_GATEWAY_HOST`
- `OCR_GATEWAY_PORT`
- `OCR_DEEPSEEK_URL`
- `OCR_GLM_URL`

Configuration code:

- `apps/qwen_tts_api/config.py`
- `apps/qwen_asr_api/config.py`
- `apps/ocr_deepseek_api/config.py`
- `apps/ocr_glm_api/config.py`
- `apps/ocr_gateway/config.py`

## Run services

```bash
cd /path/to/repo
make tts
make tts-clone
make asr
make deepseek
make ocr
make ocr-gateway
```

To bring everything up:

```bash
make all
```

To bring down the current stack:

```bash
make down
```

Direct runners:

```bash
./scripts/run/qwen-tts.sh
./scripts/run/qwen-tts-clone.sh
./scripts/run/qwen-asr.sh
./scripts/run/deepseek-ocr2.sh
./scripts/run/glm-ocr.sh
./scripts/run/ocr-gateway.sh
```

## Health checks

```bash
make health
```

Endpoints:

- `GET http://localhost:8002/health`
- `GET http://localhost:8004/health`
- `GET http://localhost:8003/health`
- `GET http://localhost:8010/health`
- `GET http://localhost:8011/health`
- `GET http://localhost:8012/health`

## `systemd --user`

The versioned units live in `systemd/user/` and are rendered using the real path of your checkout.

```bash
cd /path/to/repo
make install-user-units
systemctl --user enable --now qwen-tts.service qwen-tts-clone.service qwen-asr.service deepseek-ocr.service glm-ocr.service ocr-gateway.service
```

Logs:

```bash
journalctl --user -u qwen-tts.service -f
journalctl --user -u qwen-tts-clone.service -f
journalctl --user -u qwen-asr.service -f
journalctl --user -u deepseek-ocr.service -f
journalctl --user -u glm-ocr.service -f
journalctl --user -u ocr-gateway.service -f
```

## Notes

- `apps/ocr_gateway` exposes a unified OCR surface and delegates to internal providers.
- `apps/qwen_tts_api` shares a runtime with `packages/qwen_tts_runtime`.
- Historical documentation has been moved to `docs/archive/legacy/`.
