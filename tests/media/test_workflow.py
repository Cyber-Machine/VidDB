import asyncio

from sqlalchemy.orm import Session

from apps.media.ffprobe import MediaMetadata, parse_ffprobe_output
from apps.media.workflow import (
    run_asset_ingestion_workflow,
    verify_hls_playback_segments,
)
from apps.persistence.models import Collection, MediaAsset, ProcessingState
from apps.persistence.repositories import (
    CollectionRepository,
    MediaAssetRepository,
    MediaSegmentRepository,
    RenditionRepository,
    TenantRepository,
)


class StaticProbeAdapter:
    async def probe(self, source_uri: str) -> MediaMetadata:
        return MediaMetadata(duration_ms=1200, width=1920, height=1080)


def test_parse_ffprobe_output() -> None:
    metadata = parse_ffprobe_output(
        {
            "format": {"duration": "1.5"},
            "streams": [{"codec_type": "video", "width": 1280, "height": 720}],
        }
    )

    assert metadata == MediaMetadata(duration_ms=1500, width=1280, height=720)


def test_asset_ingestion_workflow_is_idempotent(session: Session) -> None:
    tenant = TenantRepository(session).add("tenant-a")
    collection = CollectionRepository(session, tenant.id).add(Collection(name="games"))
    asset = MediaAssetRepository(session, tenant.id).add(
        MediaAsset(collection_id=collection.id, source_uri="s3://bucket/game.mp4")
    )
    session.commit()

    asyncio.run(
        run_asset_ingestion_workflow(session, tenant.id, asset.id, StaticProbeAdapter())
    )
    asyncio.run(
        run_asset_ingestion_workflow(session, tenant.id, asset.id, StaticProbeAdapter())
    )

    reloaded = MediaAssetRepository(session, tenant.id).get(asset.id)
    assert reloaded is not None
    assert reloaded.processing_state == ProcessingState.READY
    assert reloaded.metadata_["duration_ms"] == 1200
    assert len(RenditionRepository(session, tenant.id).list()) == 3

    segments = MediaSegmentRepository(session, tenant.id).list_for_asset(asset.id)
    assert len(segments) == 1
    assert verify_hls_playback_segments(segments)
