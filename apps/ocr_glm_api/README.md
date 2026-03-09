# GLM-OCR

App HTTP: `apps/ocr_glm_api`

Runtime reusable: `packages/ocr_glm`

## Sincronizar

```bash
cd /ruta/al/repo
./scripts/sync-project.sh apps/ocr_glm_api
```

## CLI

```bash
cd /ruta/al/repo
PYTHONPATH="$PWD" uv run --project apps/ocr_glm_api python -m packages.ocr_glm.cli --input /ruta/imagen.png --mode markdown
```

Salida JSON:

```bash
PYTHONPATH="$PWD" uv run --project apps/ocr_glm_api python -m packages.ocr_glm.cli --input /ruta/imagen.png --mode text --json
```

## Servidor HTTP

```bash
./scripts/run/glm-ocr.sh
```

Endpoints:

- `POST http://localhost:8011/ocr`
- `GET http://localhost:8011/health`

## Notas

- Defaults compartidos: `packages/ocr_common/settings.py`
- Config de la app: `apps/ocr_glm_api/config.py`
- Para una interfaz OCR unificada existe `apps/ocr_gateway`
