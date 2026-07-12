import base64
import json
import mimetypes
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from urllib import request

from apps.indexing.visual import Frame

DEFAULT_LM_STUDIO_BASE_URL = "http://localhost:1234/v1"
DEFAULT_MINICPM_MODEL = "minicpm-v"


class JsonPoster(Protocol):
    def post_json(
        self,
        url: str,
        payload: Mapping[str, Any],
        timeout_seconds: float,
    ) -> dict[str, object]:
        pass


class UrllibJsonPoster:
    def post_json(
        self,
        url: str,
        payload: Mapping[str, Any],
        timeout_seconds: float,
    ) -> dict[str, object]:
        data = json.dumps(payload).encode()
        http_request = request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(http_request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode())


@dataclass(frozen=True)
class MiniCPMVProvider:
    base_url: str = DEFAULT_LM_STUDIO_BASE_URL
    model: str = DEFAULT_MINICPM_MODEL
    prompt: str = (
        "Describe this video frame for retrieval. Include visible objects, "
        "scene context, actions, text, people, and any event cues. Be concise."
    )
    timeout_seconds: float = 30.0
    poster: JsonPoster = UrllibJsonPoster()

    def describe(self, frame: Frame) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self.prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": frame_image_url(frame)},
                        },
                    ],
                }
            ],
            "temperature": 0,
        }
        response = self.poster.post_json(
            f"{self.base_url.rstrip('/')}/chat/completions",
            payload,
            self.timeout_seconds,
        )
        return _extract_description(response)


def minicpm_provider_from_env() -> MiniCPMVProvider:
    return MiniCPMVProvider(
        base_url=os.environ.get(
            "VIDEODB_LM_STUDIO_BASE_URL",
            DEFAULT_LM_STUDIO_BASE_URL,
        ),
        model=os.environ.get("VIDEODB_MINICPM_MODEL", DEFAULT_MINICPM_MODEL),
    )


def frame_image_url(frame: Frame) -> str:
    if frame.uri.startswith(("data:", "http://", "https://")):
        return frame.uri
    path = Path(frame.uri)
    if not path.exists():
        raise ValueError(
            "MiniCPM-V provider requires a local, HTTP, HTTPS, or data URL frame"
        )
    content_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode()
    return f"data:{content_type};base64,{encoded}"


def _extract_description(response: dict[str, object]) -> str:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("MiniCPM-V response did not include choices")
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise ValueError("MiniCPM-V response choice is invalid")
    message = first_choice.get("message")
    if not isinstance(message, dict):
        raise ValueError("MiniCPM-V response did not include a message")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("MiniCPM-V response content is empty")
    return content.strip()
