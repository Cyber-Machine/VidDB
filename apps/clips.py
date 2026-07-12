import hashlib
from typing import TypedDict

from sqlalchemy.orm import Session

from apps.persistence.models import MediaSegment, VirtualClip
from apps.persistence.repositories import (
    MediaSegmentRepository,
    VirtualClipRepository,
)


class RequestedSegment(TypedDict):
    asset_id: str
    start_ms: int
    end_ms: int


def create_virtual_clip(
    session: Session,
    tenant_id: str,
    name: str,
    requested_segments: list[RequestedSegment],
) -> VirtualClip:
    selected = [
        _segment_payload(segment)
        for request in requested_segments
        for segment in _source_segments(
            session,
            tenant_id,
            request["asset_id"],
            request["start_ms"],
            request["end_ms"],
        )
    ]
    clip = VirtualClipRepository(session, tenant_id).add(
        VirtualClip(
            name=name,
            manifest={
                "segments": selected,
                "copies_media_bytes": False,
            },
        )
    )
    session.commit()
    return clip


def render_clip_manifest(session: Session, tenant_id: str, clip_id: str) -> str:
    clip = VirtualClipRepository(session, tenant_id).get(clip_id)
    if clip is None:
        raise ValueError("clip not found")
    lines = ["#EXTM3U", "#EXT-X-VERSION:7"]
    for segment in clip.manifest["segments"]:
        duration = (int(segment["end_ms"]) - int(segment["start_ms"])) / 1000
        lines.append(f"#EXTINF:{duration:.3f},")
        lines.append(str(segment["object_uri"]))
    lines.append("#EXT-X-ENDLIST")
    return "\n".join(lines)


def render_compilation_manifest(
    session: Session,
    tenant_id: str,
    clip_ids: list[str],
) -> str:
    lines = ["#EXTM3U", "#EXT-X-VERSION:7"]
    for clip_id in clip_ids:
        clip = VirtualClipRepository(session, tenant_id).get(clip_id)
        if clip is None:
            raise ValueError("clip not found")
        for segment in clip.manifest["segments"]:
            duration = (int(segment["end_ms"]) - int(segment["start_ms"])) / 1000
            lines.append(f"#EXTINF:{duration:.3f},")
            lines.append(str(segment["object_uri"]))
    lines.append("#EXT-X-ENDLIST")
    return "\n".join(lines)


def signed_playback_url(clip_id: str) -> str:
    token = hashlib.sha256(clip_id.encode()).hexdigest()[:16]
    return f"/clips/{clip_id}/manifest.m3u8?token={token}"


def _source_segments(
    session: Session,
    tenant_id: str,
    asset_id: str,
    start_ms: int,
    end_ms: int,
) -> list[MediaSegment]:
    segments = MediaSegmentRepository(session, tenant_id).list_for_asset(asset_id)
    return [
        segment
        for segment in segments
        if segment.start_ms <= end_ms and start_ms <= segment.end_ms
    ]


def _segment_payload(segment: MediaSegment) -> dict[str, object]:
    return {
        "asset_id": segment.asset_id,
        "segment_id": segment.id,
        "start_ms": segment.start_ms,
        "end_ms": segment.end_ms,
        "object_uri": segment.object_uri,
    }
