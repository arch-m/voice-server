import json
import os
import tempfile
from pathlib import Path

PROMPTS = {
    "markdown": "<image>\n<|grounding|>Convert the document to markdown.",
    "text": "<image>\nFree OCR.",
}


class OcrError(RuntimeError):
    pass


def resolve_prompt(mode, prompt):
    if prompt:
        return prompt
    if mode in PROMPTS:
        return PROMPTS[mode]
    raise OcrError(f"Unsupported mode: {mode}")


def _resolve_dtype(dtype_name, device):
    import torch

    if dtype_name:
        if not hasattr(torch, dtype_name):
            raise OcrError(f"Unsupported dtype: {dtype_name}")
        return getattr(torch, dtype_name)
    if device == "cuda":
        return torch.bfloat16
    return torch.float32


def _resolve_device(device):
    import torch

    if device == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda" and not torch.cuda.is_available():
        raise OcrError("CUDA requested but not available")
    return device


def load_model(model_id, device="auto", dtype_name=None, attn_impl=None):
    from transformers import AutoModel, AutoTokenizer

    resolved_device = _resolve_device(device)
    resolved_dtype = _resolve_dtype(dtype_name, resolved_device)

    kwargs = {
        "trust_remote_code": True,
        "torch_dtype": resolved_dtype,
        "use_safetensors": True,
    }
    if attn_impl:
        kwargs["_attn_implementation"] = attn_impl

    model = AutoModel.from_pretrained(model_id, **kwargs)
    tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    model = model.eval()

    if resolved_device == "cuda":
        model = model.cuda()
    else:
        model = model.to(resolved_dtype)

    return model, tokenizer, resolved_device, resolved_dtype


def _resolve_crop_mode(crop_mode):
    if isinstance(crop_mode, bool):
        return crop_mode
    if crop_mode is None:
        return True
    if isinstance(crop_mode, str):
        lowered = crop_mode.strip().lower()
        if lowered in ("true", "1", "yes", "y"):
            return True
        if lowered in ("false", "0", "no", "n"):
            return False
    return crop_mode


def _pick_text_from_result(result):
    if isinstance(result, str):
        return result
    if isinstance(result, list):
        pieces = []
        for item in result:
            if isinstance(item, str):
                pieces.append(item)
            elif isinstance(item, dict):
                for key in ("pred", "text", "output", "response", "result"):
                    value = item.get(key)
                    if isinstance(value, str):
                        pieces.append(value)
                        break
        if pieces:
            return "\n".join(pieces)
    if isinstance(result, dict):
        for key in ("pred", "text", "output", "response", "result"):
            value = result.get(key)
            if isinstance(value, str):
                return value
            if isinstance(value, list):
                return "\n".join([str(v) for v in value])
    return None


def _read_output_text(output_dir):
    if not output_dir:
        return None
    output_dir = Path(output_dir)
    if not output_dir.exists():
        return None

    candidates = []
    for suffix in ("*.md", "*.txt"):
        candidates.extend(output_dir.glob(suffix))
    if not candidates:
        return None

    candidates.sort(key=lambda p: p.stat().st_size, reverse=True)
    try:
        return candidates[0].read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None


def _call_infer(model, tokenizer, image_path, prompt, output_dir, base_size, image_size, crop_mode, save_results):
    kwargs = {
        "prompt": prompt,
        "output_path": output_dir,
        "base_size": base_size,
        "image_size": image_size,
        "crop_mode": crop_mode,
        "save_results": save_results,
        "eval_mode": True,
    }
    try:
        return model.infer(tokenizer, image_file=image_path, **kwargs)
    except TypeError:
        try:
            return model.infer(tokenizer, image_path=image_path, **kwargs)
        except TypeError:
            return model.infer(tokenizer, image=image_path, **kwargs)


def infer_image(
    model,
    tokenizer,
    image_path,
    prompt,
    output_dir=None,
    base_size=1024,
    image_size=768,
    crop_mode=True,
    save_results=False,
):
    image_path = str(image_path)
    output_dir = output_dir or tempfile.mkdtemp(prefix="deepseek-ocr2-")
    crop_mode = _resolve_crop_mode(crop_mode)

    result = _call_infer(
        model,
        tokenizer,
        image_path=image_path,
        prompt=prompt,
        output_dir=output_dir,
        base_size=base_size,
        image_size=image_size,
        crop_mode=crop_mode,
        save_results=save_results,
    )

    text = _pick_text_from_result(result) or _read_output_text(output_dir)
    if text is None:
        text = json.dumps(result, ensure_ascii=False, indent=2)

    return text, output_dir, result


def cleanup_output_dir(output_dir, keep=False):
    if keep or not output_dir:
        return
    try:
        for root, dirs, files in os.walk(output_dir, topdown=False):
            for name in files:
                Path(root, name).unlink(missing_ok=True)
            for name in dirs:
                Path(root, name).rmdir()
        Path(output_dir).rmdir()
    except OSError:
        pass
