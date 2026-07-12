import pytest

from apps.indexing.minicpm import (
    DEFAULT_MINICPM_MODEL,
    MiniCPMVProvider,
    frame_image_url,
    minicpm_provider_from_env,
)
from apps.indexing.visual import Frame


class FakeRuntime:
    def __init__(self) -> None:
        self.model_id = ""
        self.image_url = ""
        self.prompt = ""
        self.max_new_tokens = 0
        self.downsample_mode = ""
        self.max_slice_nums = 0

    def describe_image(
        self,
        model_id: str,
        image_url: str,
        prompt: str,
        max_new_tokens: int,
        downsample_mode: str,
        max_slice_nums: int,
    ) -> str:
        self.model_id = model_id
        self.image_url = image_url
        self.prompt = prompt
        self.max_new_tokens = max_new_tokens
        self.downsample_mode = downsample_mode
        self.max_slice_nums = max_slice_nums
        return "player shoots the ball"


def test_minicpm_provider_uses_hugging_face_runtime_shape() -> None:
    runtime = FakeRuntime()
    provider = MiniCPMVProvider(runtime=runtime)

    description = provider.describe(
        Frame(timestamp_ms=500, uri="https://example.test/frame.jpg")
    )

    assert description == "player shoots the ball"
    assert runtime.model_id == "openbmb/MiniCPM-V-4.6"
    assert runtime.image_url == "https://example.test/frame.jpg"
    assert runtime.downsample_mode == "16x"
    assert runtime.max_slice_nums == 36


def test_frame_image_url_accepts_only_http_images() -> None:
    assert (
        frame_image_url(Frame(timestamp_ms=0, uri="https://example.test/frame.jpg"))
        == "https://example.test/frame.jpg"
    )

    with pytest.raises(ValueError, match="requires an HTTP or HTTPS image URL"):
        frame_image_url(Frame(timestamp_ms=0, uri="s3://derived/frame.jpg"))


def test_minicpm_provider_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VIDEODB_MINICPM_MODEL", "openbmb/MiniCPM-V-4.6")
    monkeypatch.setenv("VIDEODB_MINICPM_DOWNSAMPLE_MODE", "4x")
    monkeypatch.setenv("VIDEODB_MINICPM_MAX_SLICE_NUMS", "12")
    monkeypatch.setenv("VIDEODB_MINICPM_MAX_NEW_TOKENS", "128")

    provider = minicpm_provider_from_env()

    assert provider.model_id == DEFAULT_MINICPM_MODEL
    assert provider.downsample_mode == "4x"
    assert provider.max_slice_nums == 12
    assert provider.max_new_tokens == 128
