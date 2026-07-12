from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from apps.indexing.minicpm import (
    MiniCPMVProvider,
    frame_image_url,
    minicpm_provider_from_env,
)
from apps.indexing.visual import Frame


class FakePoster:
    def __init__(self) -> None:
        self.url = ""
        self.payload: Mapping[str, Any] = {}

    def post_json(
        self,
        url: str,
        payload: Mapping[str, Any],
        timeout_seconds: float,
    ) -> dict[str, object]:
        self.url = url
        self.payload = payload
        return {"choices": [{"message": {"content": "player shoots the ball"}}]}


def test_minicpm_provider_calls_lm_studio_chat_completions() -> None:
    poster = FakePoster()
    provider = MiniCPMVProvider(
        base_url="http://localhost:1234/v1",
        model="openbmb/minicpm-v",
        poster=poster,
    )

    description = provider.describe(
        Frame(timestamp_ms=500, uri="data:image/jpeg;base64,abc")
    )

    assert description == "player shoots the ball"
    assert poster.url == "http://localhost:1234/v1/chat/completions"
    assert poster.payload["model"] == "openbmb/minicpm-v"


def test_frame_image_url_encodes_local_frame(tmp_path: Path) -> None:
    frame_path = tmp_path / "frame.jpg"
    frame_path.write_bytes(b"fake-jpeg")

    image_url = frame_image_url(Frame(timestamp_ms=0, uri=str(frame_path)))

    assert image_url.startswith("data:image/jpeg;base64,")


def test_frame_image_url_rejects_unavailable_frame() -> None:
    with pytest.raises(ValueError, match="requires a local"):
        frame_image_url(Frame(timestamp_ms=0, uri="s3://derived/frame.jpg"))


def test_minicpm_provider_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VIDEODB_LM_STUDIO_BASE_URL", "http://lmstudio.test/v1")
    monkeypatch.setenv("VIDEODB_MINICPM_MODEL", "minicpm-v-4.6")

    provider = minicpm_provider_from_env()

    assert provider.base_url == "http://lmstudio.test/v1"
    assert provider.model == "minicpm-v-4.6"
