"""Wrappers para los modelos Qwen3 TTS y ASR."""

from typing import Optional, Tuple, Union

import numpy as np
import torch
from qwen_tts import Qwen3TTSModel, Qwen3TTSTokenizer


class QwenTTS:
    """Wrapper para Qwen3-TTS con interfaz simplificada."""

    def __init__(self, model_path: str, device: str = "cuda:0", dtype=torch.bfloat16):
        """
        Inicializa el modelo TTS.

        Args:
            model_path: Ruta del modelo en HuggingFace
            device: Dispositivo (cuda:0, cpu, etc.)
            dtype: Tipo de datos (torch.bfloat16, torch.float16, etc.)
        """
        self.model_path = model_path
        self.device = device
        self.dtype = dtype

        print(f"Cargando tokenizador TTS...")
        self.tokenizer = Qwen3TTSTokenizer.from_pretrained(
            "Qwen/Qwen3-TTS-Tokenizer-12Hz"
        )

        print(f"Cargando modelo TTS desde {model_path}...")
        self.model = Qwen3TTSModel.from_pretrained(
            model_path, device_map=device, dtype=dtype
        )
        print("Modelo TTS cargado exitosamente")

    def generate(
        self,
        text: str,
        language: str = "Spanish",
        speaker: str = None,
        instruct: str = None,
    ) -> Tuple[np.ndarray, int]:
        """
        Genera audio desde texto.

        Args:
            text: Texto a sintetizar
            language: Idioma (Spanish, English, etc.)
            speaker: Voz a usar (opcional, default: vivian)
            instruct: Instrucciones adicionales (opcional)

        Returns:
            Tuple (audio, sample_rate)
        """
        if not speaker:
            speaker = "vivian"

        wavs, sample_rate = self.model.generate_custom_voice(
            text=text, speaker=speaker, language=language, instruct=instruct
        )

        return wavs[0], int(sample_rate)


class QwenVoiceClone:
    """Wrapper para Qwen3-TTS Base con clonacion de voz."""

    def __init__(self, model_path: str, device: str = "cuda:0", dtype=torch.bfloat16):
        """
        Inicializa el modelo Base para voice cloning.

        Args:
            model_path: Ruta del modelo Base en HuggingFace
            device: Dispositivo (cuda:0, cpu, etc.)
            dtype: Tipo de datos (torch.bfloat16, torch.float16, etc.)
        """
        self.model_path = model_path
        self.device = device
        self.dtype = dtype

        print("Cargando tokenizador TTS...")
        self.tokenizer = Qwen3TTSTokenizer.from_pretrained(
            "Qwen/Qwen3-TTS-Tokenizer-12Hz"
        )

        print(f"Cargando modelo TTS Base desde {model_path}...")
        self.model = Qwen3TTSModel.from_pretrained(
            model_path,
            device_map=device,
            dtype=dtype,
        )
        print("Modelo TTS Base cargado exitosamente")

    def generate(
        self,
        text: str,
        language: str,
        ref_audio: Union[str, np.ndarray],
        ref_sr: Optional[int] = None,
        ref_text: Optional[str] = None,
        x_vector_only_mode: bool = False,
    ) -> Tuple[np.ndarray, int]:
        """
        Genera audio por clonacion de voz usando un audio de referencia.

        Returns:
            Tuple (audio, sample_rate)
        """
        if isinstance(ref_audio, str):
            ref_input = ref_audio
        else:
            if ref_sr is None:
                raise ValueError("ref_sr es requerido cuando ref_audio es np.ndarray")
            ref_input = (ref_audio, ref_sr)

        wavs, sample_rate = self.model.generate_voice_clone(
            text=text,
            language=language,
            ref_audio=ref_input,
            ref_text=ref_text,
            x_vector_only_mode=x_vector_only_mode,
        )
        return wavs[0], int(sample_rate)


class QwenASR:
    """Wrapper para Qwen3-ASR con interfaz simplificada."""

    def __init__(self, model_path: str, device: str = "cuda:0", dtype=torch.bfloat16):
        """
        Inicializa el modelo ASR.

        Args:
            model_path: Ruta del modelo en HuggingFace
            device: Dispositivo (cuda:0, cpu, etc.)
            dtype: Tipo de datos (torch.bfloat16, torch.float16, etc.)
        """
        self.model_path = model_path
        self.device = device
        self.dtype = dtype

        try:
            from qwen_asr import Qwen3ASRModel

            print(f"Cargando modelo ASR desde {model_path}...")
            self.model = Qwen3ASRModel.from_pretrained(
                model_path, device_map=device, dtype=dtype
            )
            print("Modelo ASR cargado exitosamente")
        except ImportError as e:
            print(f"Error: qwen_asr no disponible. Instalar en entorno separado.")
            raise e

    def transcribe(
        self, audio: np.ndarray, sample_rate: int = 16000, language: str = "Spanish"
    ) -> dict:
        """
        Transcribe audio a texto.

        Args:
            audio: Array numpy con audio
            sample_rate: Frecuencia de muestreo del audio
            language: Idioma esperado

        Returns:
            Dict con 'text' y metadatos
        """

        results = self.model.transcribe(audio=(audio, sample_rate), language=language)

        if results:
            return {
                "text": results[0].text,
                "language": results[0].language or language,
            }
        return {"text": "", "language": language}
