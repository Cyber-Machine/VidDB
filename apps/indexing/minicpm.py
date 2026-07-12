import importlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from apps.indexing.visual import Frame

DEFAULT_MINICPM_MODEL = "openbmb/MiniCPM-V-4.6"


class MiniCPMRuntime(Protocol):
    def describe_image(
        self,
        model_id: str,
        image_url: str,
        prompt: str,
        max_new_tokens: int,
        downsample_mode: str,
        max_slice_nums: int,
    ) -> str:
        pass


class TransformersMiniCPMRuntime:
    def __init__(self) -> None:
        self.model_id = ""
        self.processor: Any | None = None
        self.model: Any | None = None

    def describe_image(
        self,
        model_id: str,
        image_url: str,
        prompt: str,
        max_new_tokens: int,
        downsample_mode: str,
        max_slice_nums: int,
    ) -> str:
        processor, model = self._load(model_id)
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "url": image_url},
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
            downsample_mode=downsample_mode,
            max_slice_nums=max_slice_nums,
        ).to(model.device)
        generated_ids = model.generate(
            **inputs,
            downsample_mode=downsample_mode,
            max_new_tokens=max_new_tokens,
        )
        generated_ids_trimmed = [
            output_ids[len(input_ids) :]
            for input_ids, output_ids in zip(inputs.input_ids, generated_ids)
        ]
        output_text = processor.batch_decode(
            generated_ids_trimmed,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )
        return _clean_description(output_text[0])

    def _load(self, model_id: str) -> tuple[Any, Any]:
        if (
            self.processor is not None
            and self.model is not None
            and self.model_id == model_id
        ):
            return self.processor, self.model
        try:
            transformers = importlib.import_module("transformers")
        except ImportError as error:
            raise RuntimeError(
                "MiniCPM-V requires Hugging Face dependencies. Install "
                '`transformers[torch]`, `torch`, and `torchvision` before use.'
            ) from error

        self.processor = transformers.AutoProcessor.from_pretrained(model_id)
        self.model = transformers.AutoModelForImageTextToText.from_pretrained(
            model_id,
            torch_dtype="auto",
            device_map="auto",
        )
        self.model_id = model_id
        return self.processor, self.model


@dataclass(frozen=True)
class MiniCPMVProvider:
    model_id: str = DEFAULT_MINICPM_MODEL
    prompt: str = (
        "Describe this video frame for retrieval. Include visible objects, "
        "scene context, actions, text, people, and event cues. Be concise."
    )
    max_new_tokens: int = 256
    downsample_mode: str = "16x"
    max_slice_nums: int = 36
    runtime: MiniCPMRuntime = TransformersMiniCPMRuntime()

    def describe(self, frame: Frame) -> str:
        return self.runtime.describe_image(
            self.model_id,
            frame_image_url(frame),
            self.prompt,
            self.max_new_tokens,
            self.downsample_mode,
            self.max_slice_nums,
        )


def minicpm_provider_from_env() -> MiniCPMVProvider:
    return MiniCPMVProvider(
        model_id=os.environ.get("VIDEODB_MINICPM_MODEL", DEFAULT_MINICPM_MODEL),
        downsample_mode=os.environ.get("VIDEODB_MINICPM_DOWNSAMPLE_MODE", "16x"),
        max_slice_nums=int(os.environ.get("VIDEODB_MINICPM_MAX_SLICE_NUMS", "36")),
        max_new_tokens=int(os.environ.get("VIDEODB_MINICPM_MAX_NEW_TOKENS", "256")),
    )


def frame_image_url(frame: Frame) -> str:
    if frame.uri.startswith(("http://", "https://")):
        return frame.uri
    path = Path(frame.uri)
    if path.exists():
        return str(path)
    raise ValueError(
        "MiniCPM-V Hugging Face provider requires an HTTP, HTTPS, or local image"
    )


def _clean_description(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("MiniCPM-V response content is empty")
    return value.strip()
