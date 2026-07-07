import asyncio
import json
import subprocess
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class MediaMetadata:
    duration_ms: int
    width: int | None
    height: int | None


class ProbeAdapter(Protocol):
    async def probe(self, source_uri: str) -> MediaMetadata:
        pass


class FfprobeAdapter:
    async def probe(self, source_uri: str) -> MediaMetadata:
        return await asyncio.to_thread(self._probe_sync, source_uri)

    def _probe_sync(self, source_uri: str) -> MediaMetadata:
        completed = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                source_uri,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return parse_ffprobe_output(json.loads(completed.stdout))


def parse_ffprobe_output(payload: dict[str, Any]) -> MediaMetadata:
    format_ = payload.get("format", {})
    duration_seconds = float(format_.get("duration", 0))
    video_stream = next(
        (
            stream
            for stream in payload.get("streams", [])
            if stream.get("codec_type") == "video"
        ),
        {},
    )
    return MediaMetadata(
        duration_ms=int(duration_seconds * 1000),
        width=video_stream.get("width"),
        height=video_stream.get("height"),
    )
