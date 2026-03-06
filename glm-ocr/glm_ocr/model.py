import importlib
import json
import os
import re
import tempfile
from pathlib import Path

PROMPTS = {
    "markdown": "Text Recognition:",
    "text": "Text Recognition:",
}

_SPECIAL_TOKEN_RE = re.compile(r"<\|[^<>|]+\|>")


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
        normalized = dtype_name.replace("torch.", "")
        if not hasattr(torch, normalized):
            raise OcrError(f"Unsupported dtype: {dtype_name}")
        return getattr(torch, normalized)
    if isinstance(device, str) and device.startswith("cuda"):
        return torch.bfloat16
    return torch.float32


def _resolve_device(device):
    import torch

    if device == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    if isinstance(device, str) and device.startswith("cuda") and not torch.cuda.is_available():
        raise OcrError("CUDA requested but not available")
    if device not in ("cpu", "cuda") and not (isinstance(device, str) and device.startswith("cuda:")):
        raise OcrError(f"Unsupported device: {device}")
    return device


def _patch_video_processor_lookup():
    """Work around transformers mapping entries that may be None."""
    try:
        from transformers.models.auto import video_processing_auto as video_auto
    except Exception:
        return

    current = getattr(video_auto, "video_processor_class_from_name", None)
    if current is None or getattr(current, "_glm_ocr_patched", False):
        return

    def _safe_video_processor_class_from_name(class_name: str):
        for module_name, extractors in video_auto.VIDEO_PROCESSOR_MAPPING_NAMES.items():
            if not extractors:
                continue
            if class_name in extractors:
                module_name = video_auto.model_type_to_module_name(module_name)
                module = importlib.import_module(f".{module_name}", "transformers.models")
                try:
                    return getattr(module, class_name)
                except AttributeError:
                    continue

        for extractor in video_auto.VIDEO_PROCESSOR_MAPPING._extra_content.values():
            if getattr(extractor, "__name__", None) == class_name:
                return extractor

        main_module = importlib.import_module("transformers")
        if hasattr(main_module, class_name):
            return getattr(main_module, class_name)

        return None

    _safe_video_processor_class_from_name._glm_ocr_patched = True
    video_auto.video_processor_class_from_name = _safe_video_processor_class_from_name


def load_model(model_id, device="auto", dtype_name=None, attn_impl=None):
    from transformers import AutoModelForImageTextToText, AutoProcessor

    resolved_device = _resolve_device(device)
    resolved_dtype = _resolve_dtype(dtype_name, resolved_device)
    _patch_video_processor_lookup()
    if (
        attn_impl == "flash_attention_2"
        and isinstance(resolved_device, str)
        and not resolved_device.startswith("cuda")
    ):
        attn_impl = "eager"

    kwargs = {
        "torch_dtype": resolved_dtype,
        "trust_remote_code": True,
    }
    if attn_impl:
        kwargs["attn_implementation"] = attn_impl

    model = AutoModelForImageTextToText.from_pretrained(model_id, **kwargs)
    processor = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
    model = model.eval().to(resolved_device)

    return model, processor, resolved_device, resolved_dtype


def _prepare_inputs(processor, image_path, prompt):
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "url": image_path},
                {"type": "text", "text": prompt},
            ],
        }
    ]

    inputs = processor.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_dict=True,
        return_tensors="pt",
    )
    if "token_type_ids" in inputs:
        del inputs["token_type_ids"]
    return inputs


def _move_to_device(inputs, device):
    if hasattr(inputs, "to"):
        return inputs.to(device)

    moved = {}
    for key, value in inputs.items():
        moved[key] = value.to(device) if hasattr(value, "to") else value
    return moved


def _clean_decoded_text(text):
    text = _SPECIAL_TOKEN_RE.sub("", text or "")
    text = text.replace("\x00", "")
    return text.strip()


def _call_infer(model, processor, image_path, prompt, max_new_tokens):
    import torch

    inputs = _prepare_inputs(processor, image_path=image_path, prompt=prompt)
    inputs = _move_to_device(inputs, model.device)
    prompt_len = int(inputs["input_ids"].shape[-1]) if "input_ids" in inputs else 0

    with torch.inference_mode():
        generated = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
        )

    generated_tokens = generated[:, prompt_len:]
    decoded = processor.decode(generated_tokens[0], skip_special_tokens=False)
    cleaned = _clean_decoded_text(decoded)
    if not cleaned:
        cleaned = processor.decode(generated_tokens[0], skip_special_tokens=True).strip()

    result = {
        "text": cleaned,
        "raw_text": decoded,
        "generated_tokens": int(generated_tokens.shape[-1]),
    }
    return result


def _write_outputs(output_dir, result):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    text_file = output_path / "ocr.txt"
    text_file.write_text(result.get("text", ""), encoding="utf-8")

    json_file = output_path / "raw.json"
    json_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


def infer_image(
    model,
    processor,
    image_path,
    prompt,
    output_dir=None,
    base_size=1024,
    image_size=768,
    crop_mode=True,
    save_results=False,
    max_new_tokens=8192,
):
    del base_size, image_size, crop_mode

    image_path = str(image_path)
    keep_output = bool(output_dir) or bool(save_results)
    output_dir = output_dir or tempfile.mkdtemp(prefix="glm-ocr-")

    result = _call_infer(
        model,
        processor,
        image_path=image_path,
        prompt=prompt,
        max_new_tokens=max_new_tokens,
    )
    text = result["text"]

    if keep_output:
        _write_outputs(output_dir, result)

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
