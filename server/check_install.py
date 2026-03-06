#!/usr/bin/env python3
"""
Script para verificar la instalación de Qwen TTS y ASR
"""
import sys
import importlib

def check_module(module_name, env_name):
    """Verifica si un módulo puede ser importado"""
    try:
        mod = importlib.import_module(module_name)
        version = getattr(mod, '__version__', 'unknown')
        print(f"✓ {env_name}: {module_name} v{version}")
        return True
    except ImportError as e:
        print(f"✗ {env_name}: {module_name} - ERROR: {e}")
        return False

def check_tts():
    """Verifica entorno TTS"""
    print("\n=== Qwen TTS Environment ===")
    modules = ['qwen_tts', 'transformers', 'torch', 'torchaudio', 'librosa', 'gradio']
    return all(check_module(m, 'TTS') for m in modules)

def check_asr():
    """Verifica entorno ASR"""
    print("\n=== Qwen ASR Environment ===")
    modules = ['qwen_asr', 'transformers', 'torch', 'vllm']
    return all(check_module(m, 'ASR') for m in modules)

if __name__ == "__main__":
    env = sys.argv[1] if len(sys.argv) > 1 else 'both'

    if env == 'tts':
        success = check_tts()
    elif env == 'asr':
        success = check_asr()
    else:
        success = check_tts() and check_asr()

    sys.exit(0 if success else 1)
