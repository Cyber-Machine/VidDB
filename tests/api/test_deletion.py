from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from apps.api.main import app, get_session
from apps.hardening import RateLimiter, TenantQuota, metrics_snapshot
from apps.indexing.transcript import MetadataASRProvider, build_transcript_index
from apps.media.workflow import create_proxy_rendition, generate_cmaf_hls_fragments
from apps.persistence.models import Collection, MediaAsset, ProcessingState
from apps.persistence.repositories import (
    AuditRecordRepository,
    CollectionRepository,
    MediaAssetRepository,
    MediaSegmentRepository,
    RenditionRepository,
    TemporalRecordRepository,
    TenantRepository,
)


def test_asset_deletion_tombstones_and_removes_derived_rows(session: Session) -> None:
    tenant = TenantRepository(session).add("tenant-a")
    collection = CollectionRepository(session, tenant.id).add(Collection(name="games"))
    asset = MediaAssetRepository(session, tenant.id).add(
        MediaAsset(
            collection_id=collection.id,
            source_uri="s3://bucket/game.mp4",
            metadata_={
                "transcript": [
                    {"start_ms": 0, "end_ms": 100, "text": "goal"},
                ]
            },
        )
    )
    session.commit()
    create_proxy_rendition(session, tenant.id, asset.id)
    generate_cmaf_hls_fragments(session, tenant.id, asset.id, 1000)
    build_transcript_index(session, tenant.id, asset.id, "v1", MetadataASRProvider())
    session.commit()

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_session] = override_session
    client = TestClient(app)
    response = client.delete(f"/assets/{asset.id}", headers={"X-Tenant-ID": tenant.id})

    assert response.status_code == 200
    assert response.json()["status"] == "complete"
    assert response.json()["deleted_objects"]
    reloaded = MediaAssetRepository(session, tenant.id).get(asset.id)
    assert reloaded is not None
    assert reloaded.processing_state == ProcessingState.DELETED
    assert reloaded.metadata_["tombstone"] is True
    assert RenditionRepository(session, tenant.id).list() == []
    assert MediaSegmentRepository(session, tenant.id).list() == []
    assert TemporalRecordRepository(session, tenant.id).list() == []
    assert AuditRecordRepository(session, tenant.id).list_for_subject(asset.id)

    status = client.get(
        f"/assets/{asset.id}/deletion",
        headers={"X-Tenant-ID": tenant.id},
    )
    assert status.json()["status"] == "complete"
    app.dependency_overrides.clear()


def test_hardening_helpers_track_quota_rate_and_metrics(session: Session) -> None:
    tenant = TenantRepository(session).add("tenant-a")
    collection = CollectionRepository(session, tenant.id).add(Collection(name="games"))
    MediaAssetRepository(session, tenant.id).add(
        MediaAsset(collection_id=collection.id, source_uri="s3://bucket/game.mp4")
    )
    session.commit()

    assert TenantQuota(max_assets=2).allows_asset_count(1)
    limiter = RateLimiter(max_requests=1)
    assert limiter.allow(tenant.id)
    assert not limiter.allow(tenant.id)
    assert metrics_snapshot(session, tenant.id)["assets"] == 1
