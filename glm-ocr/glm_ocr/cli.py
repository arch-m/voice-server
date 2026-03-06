import argparse
import json
import os
import sys

from .model import (
    OcrError,
    cleanup_output_dir,
    infer_image,
    load_model,
    resolve_prompt,
)


def _parse_args(argv):
    parser = argparse.ArgumentParser(description="GLM OCR CLI")
    parser.add_argument("--input", required=True, help="Path to an image file")
    parser.add_argument(
        "--mode",
        default="markdown",
        choices=["markdown", "text"],
        help="Prompt preset to use",
    )
    parser.add_argument("--prompt", help="Override prompt text")
    parser.add_argument(
        "--model",
        default="zai-org/GLM-OCR",
        help="Model id on Hugging Face",
    )
    parser.add_argument(
        "--device",
        default="auto",
        choices=["auto", "cuda", "cpu"],
        help="Device selection",
    )
    parser.add_argument("--dtype", default=None, help="Torch dtype name")
    parser.add_argument(
        "--attn",
        default=None,
        help="Attention implementation (flash_attention_2, sdpa, eager)",
    )
    parser.add_argument(
        "--base-size",
        type=int,
        default=1024,
        help="Compatibility flag (unused in GLM-OCR)",
    )
    parser.add_argument(
        "--image-size",
        type=int,
        default=768,
        help="Compatibility flag (unused in GLM-OCR)",
    )
    parser.add_argument(
        "--crop-mode",
        default="true",
        help="Compatibility flag (unused in GLM-OCR)",
    )
    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=8192,
        help="Maximum number of generated tokens",
    )
    parser.add_argument(
        "--save-results",
        action="store_true",
        help="Save OCR text and raw JSON to output dir",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for model outputs (defaults to temp)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Write extracted text to this file",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON with text and metadata",
    )
    return parser.parse_args(argv)


def _validate_input(path):
    if not os.path.exists(path):
        raise OcrError(f"Input not found: {path}")


def main(argv=None):
    args = _parse_args(argv or sys.argv[1:])

    try:
        _validate_input(args.input)
        prompt = resolve_prompt(args.mode, args.prompt)

        if args.attn is None:
            if args.device == "cpu":
                args.attn = "eager"
            elif args.device == "cuda":
                args.attn = "flash_attention_2"
            else:
                import torch

                args.attn = "flash_attention_2" if torch.cuda.is_available() else "eager"

        model, processor, device, dtype = load_model(
            args.model,
            device=args.device,
            dtype_name=args.dtype,
            attn_impl=args.attn,
        )

        text, output_dir, raw = infer_image(
            model,
            processor,
            image_path=args.input,
            prompt=prompt,
            output_dir=args.output_dir,
            base_size=args.base_size,
            image_size=args.image_size,
            crop_mode=args.crop_mode,
            save_results=args.save_results,
            max_new_tokens=args.max_new_tokens,
        )

        if args.output:
            with open(args.output, "w", encoding="utf-8") as handle:
                handle.write(text)

        if args.json:
            payload = {
                "text": text,
                "input": args.input,
                "mode": args.mode,
                "prompt": prompt,
                "model": args.model,
                "device": device,
                "dtype": str(dtype),
                "max_new_tokens": args.max_new_tokens,
                "output_dir": output_dir,
                "raw": raw,
            }
            print(json.dumps(payload, ensure_ascii=False))
        else:
            print(text)

        cleanup_output_dir(output_dir, keep=args.save_results or bool(args.output_dir))

    except OcrError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # pragma: no cover - safeguard for CLI
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
