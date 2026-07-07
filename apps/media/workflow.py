from sqlalchemy.orm import Session

from apps.media.ffprobe import ProbeAdapter
from apps.persistence.models import (
    MediaSegment,
    ProcessingState,
    Rendition,
)
from apps.persistence.repositories import (
    MediaAssetRepository,
    MediaSegmentRepository,
    RenditionRepository,
)


async def run_asset_ingestion_workflow(
    session: Session,
    tenant_id: str,
    asset_id: str,
    probe_adapter: ProbeAdapter,
) -> None:
    asset = MediaAssetRepository(session, tenant_id).get(asset_id)
    if asset is None:
        raise ValueError("asset not found")

    asset.processing_state = ProcessingState.PROCESSING
    metadata = await probe_adapter.probe(asset.source_uri)
    asset.metadata_ = {
        **asset.metadata_,
        "duration_ms": metadata.duration_ms,
        "width": metadata.width,
        "height": metadata.height,
    }
    extract_audio(session, tenant_id, asset.id)
    create_proxy_rendition(session, tenant_id, asset.id)
    generate_cmaf_hls_fragments(session, tenant_id, asset.id, metadata.duration_ms)
    generate_thumbnails(session, tenant_id, asset.id)
    asset.processing_state = ProcessingState.READY
    session.commit()


def extract_audio(session: Session, tenant_id: str, asset_id: str) -> Rendition:
    return _ensure_rendition(session, tenant_id, asset_id, "audio")


def create_proxy_rendition(
    session: Session,
    tenant_id: str,
    asset_id: str,
) -> Rendition:
    return _ensure_rendition(session, tenant_id, asset_id, "proxy")


def generate_thumbnails(session: Session, tenant_id: str, asset_id: str) -> Rendition:
    return _ensure_rendition(session, tenant_id, asset_id, "thumbnail")


def generate_cmaf_hls_fragments(
    session: Session,
    tenant_id: str,
    asset_id: str,
    duration_ms: int,
) -> list[MediaSegment]:
    segments = MediaSegmentRepository(session, tenant_id)
    existing = segments.list_for_asset(asset_id)
    if existing:
        return existing
    end_ms = max(duration_ms, 1000)
    return [
        segments.add(
            MediaSegment(
                asset_id=asset_id,
                start_ms=0,
                end_ms=end_ms,
                object_uri=f"s3://derived/{asset_id}/hls/segment-0.m4s",
            )
        )
    ]


def verify_hls_playback_segments(segments: list[MediaSegment]) -> bool:
    return bool(segments) and segments[0].start_ms == 0 and all(
        segment.end_ms > segment.start_ms for segment in segments
    )


def _ensure_rendition(
    session: Session,
    tenant_id: str,
    asset_id: str,
    kind: str,
) -> Rendition:
    renditions = RenditionRepository(session, tenant_id)
    existing = renditions.get_for_asset_and_kind(asset_id, kind)
    if existing is not None:
        return existing
    return renditions.add(
        Rendition(
            asset_id=asset_id,
            kind=kind,
            object_uri=f"s3://derived/{asset_id}/{kind}",
        )
    )
