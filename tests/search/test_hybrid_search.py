from time import perf_counter

from sqlalchemy.orm import Session

from apps.indexing.transcript import MetadataASRProvider, build_transcript_index
from apps.indexing.visual import DeterministicVisualProvider, build_visual_index
from apps.persistence.models import Collection, MediaAsset, MediaSegment
from apps.persistence.repositories import (
    CollectionRepository,
    MediaAssetRepository,
    MediaSegmentRepository,
    TenantRepository,
)
from apps.search import hybrid_search


def test_hybrid_search_filters_and_merges_temporal_results(session: Session) -> None:
    tenant = TenantRepository(session).add("tenant-a")
    collection = CollectionRepository(session, tenant.id).add(Collection(name="games"))
    other_collection = CollectionRepository(session, tenant.id).add(
        Collection(name="news")
    )
    asset = _indexed_asset(session, tenant.id, collection.id)
    _indexed_asset(session, tenant.id, other_collection.id)

    response = hybrid_search(
        session=session,
        tenant_id=tenant.id,
        query="goal",
        collection_ids=[collection.id],
        asset_ids=[asset.id],
        start_ms=200,
        end_ms=800,
        modalities=["transcript", "visual"],
        index_versions=["v1"],
        pre_roll_ms=100,
        post_roll_ms=200,
    )

    results = response["results"]
    assert len(results) == 1
    result = results[0]
    assert result["asset_id"] == asset.id
    assert result["start_ms"] == 0
    assert result["end_ms"] == 1200
    assert result["modalities"] == ["transcript", "visual"]
    assert "goal scored" in result["evidence"]
    assert result["source_frame_uris"]


def test_hybrid_search_uses_cursor_pagination(session: Session) -> None:
    tenant = TenantRepository(session).add("tenant-a")
    collection = CollectionRepository(session, tenant.id).add(Collection(name="games"))
    _indexed_asset(session, tenant.id, collection.id, source_uri="s3://bucket/one.mp4")
    _indexed_asset(session, tenant.id, collection.id, source_uri="s3://bucket/two.mp4")

    first_page = hybrid_search(
        session=session,
        tenant_id=tenant.id,
        query="goal",
        limit=1,
    )
    second_page = hybrid_search(
        session=session,
        tenant_id=tenant.id,
        query="goal",
        cursor=first_page["next_cursor"],
        limit=1,
    )

    assert first_page["next_cursor"] == "1"
    assert first_page["results"][0]["asset_id"] != second_page["results"][0]["asset_id"]


def test_warm_hybrid_search_p95_is_bounded(session: Session) -> None:
    tenant = TenantRepository(session).add("tenant-a")
    collection = CollectionRepository(session, tenant.id).add(Collection(name="games"))
    for index in range(12):
        _indexed_asset(
            session,
            tenant.id,
            collection.id,
            source_uri=f"s3://bucket/{index}.mp4",
        )

    durations = []
    for _ in range(20):
        started_at = perf_counter()
        hybrid_search(session=session, tenant_id=tenant.id, query="goal")
        durations.append(perf_counter() - started_at)

    p95 = sorted(durations)[18]
    assert p95 < 0.05


def _indexed_asset(
    session: Session,
    tenant_id: str,
    collection_id: str,
    source_uri: str = "s3://bucket/game.mp4",
) -> MediaAsset:
    asset = MediaAssetRepository(session, tenant_id).add(
        MediaAsset(
            collection_id=collection_id,
            source_uri=source_uri,
            metadata_={
                "transcript": [
                    {"start_ms": 0, "end_ms": 1000, "text": "goal scored"},
                ]
            },
        )
    )
    MediaSegmentRepository(session, tenant_id).add(
        MediaSegment(
            asset_id=asset.id,
            start_ms=0,
            end_ms=1000,
            object_uri=f"s3://segments/{asset.id}",
        )
    )
    session.commit()
    build_transcript_index(session, tenant_id, asset.id, "v1", MetadataASRProvider())
    build_visual_index(
        session,
        tenant_id,
        asset.id,
        "v1",
        DeterministicVisualProvider(),
    )
    return asset
