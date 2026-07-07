import pytest
from sqlalchemy.orm import Session

from apps.indexing.visual import (
    DeterministicVisualProvider,
    build_visual_index,
    extract_shots,
    representative_frames,
    visual_vector_search,
)
from apps.persistence.models import (
    Collection,
    MediaAsset,
    MediaSegment,
    ProcessingState,
    Tenant,
)
from apps.persistence.repositories import (
    CollectionRepository,
    MediaAssetRepository,
    MediaSegmentRepository,
    TemporalRecordRepository,
    TenantRepository,
)


class FailingVisualProvider:
    def describe(self, frame: object) -> str:
        raise RuntimeError("visual branch failed")


def test_visual_index_persists_frame_evidence(session: Session) -> None:
    tenant, asset = _asset_with_segment(session)

    shots = extract_shots(session, tenant.id, asset.id)
    frames = representative_frames(asset.id, shots)
    index = build_visual_index(
        session,
        tenant.id,
        asset.id,
        "v1",
        DeterministicVisualProvider(),
    )

    records = TemporalRecordRepository(session, tenant.id).list_for_index(index.id)
    results = visual_vector_search(session, tenant.id, index.id, "representative")

    assert shots[0].start_ms == 0
    assert frames[0].timestamp_ms == 500
    assert records[0].payload["source_frame_uri"] == frames[0].uri
    assert results[0]["source_frame_uri"] == frames[0].uri


def test_visual_index_failure_marks_asset_partially_ready(session: Session) -> None:
    tenant, asset = _asset_with_segment(session)

    with pytest.raises(RuntimeError, match="visual branch failed"):
        build_visual_index(
            session,
            tenant.id,
            asset.id,
            "v1",
            FailingVisualProvider(),
        )

    reloaded = MediaAssetRepository(session, tenant.id).get(asset.id)
    assert reloaded is not None
    assert reloaded.processing_state == ProcessingState.PARTIALLY_READY


def _asset_with_segment(session: Session) -> tuple[Tenant, MediaAsset]:
    tenant = TenantRepository(session).add("tenant-a")
    collection = CollectionRepository(session, tenant.id).add(Collection(name="games"))
    asset = MediaAssetRepository(session, tenant.id).add(
        MediaAsset(collection_id=collection.id, source_uri="s3://bucket/game.mp4")
    )
    MediaSegmentRepository(session, tenant.id).add(
        MediaSegment(
            asset_id=asset.id,
            start_ms=0,
            end_ms=1000,
            object_uri="s3://segment",
        )
    )
    session.commit()
    return tenant, asset
