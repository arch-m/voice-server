# DeepSeek OCR 2

App HTTP: `apps/ocr_deepseek_api`

Runtime reusable: `packages/ocr_deepseek`

## Sincronizar

```bash
cd /ruta/al/repo
./scripts/sync-project.sh apps/ocr_deepseek_api
```

## CLI

```bash
cd /ruta/al/repo
PYTHONPATH="$PWD" uv run --project apps/ocr_deepseek_api python -m packages.ocr_deepseek.cli --input /ruta/imagen.png --mode markdown
```

Salida JSON:

```bash
PYTHONPATH="$PWD" uv run --project apps/ocr_deepseek_api python -m packages.ocr_deepseek.cli --input /ruta/imagen.png --mode text --json
```

## Servidor HTTP

```bash
./scripts/run/deepseek-ocr2.sh
```

Endpoints:

- `POST http://localhost:8010/ocr`
- `GET http://localhost:8010/health`

## Notas

- Defaults compartidos: `packages/ocr_common/settings.py`
- Config de la app: `apps/ocr_deepseek_api/config.py`
- Código histórico removido del árbol activo; ver `docs/archive/legacy/` si necesitas contexto viejo
