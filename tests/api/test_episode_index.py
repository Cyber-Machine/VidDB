from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from apps.api.main import app, get_session
from apps.indexing.transcript import MetadataASRProvider, build_transcript_index
from apps.persistence.models import Collection, MediaAsset
from apps.persistence.repositories import (
    CollectionRepository,
    MediaAssetRepository,
    TenantRepository,
)


def test_build_episode_index_endpoint_is_tenant_scoped(session: Session) -> None:
    tenant = TenantRepository(session).add("tenant-a")
    other_tenant = TenantRepository(session).add("tenant-b")
    collection = CollectionRepository(session, tenant.id).add(Collection(name="games"))
    asset = MediaAssetRepository(session, tenant.id).add(
        MediaAsset(
            collection_id=collection.id,
            source_uri="s3://bucket/game.mp4",
            metadata_={
                "transcript": [
                    {"start_ms": 0, "end_ms": 500, "text": "goal scored"}
                ]
            },
        )
    )
    session.commit()
    source = build_transcript_index(
        session, tenant.id, asset.id, "v1", MetadataASRProvider()
    )

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_session] = override_session
    client = TestClient(app)
    request = {"source_index_id": source.id, "version": "transcript-v1"}
    response = client.post(
        f"/assets/{asset.id}/episodes",
        headers={"X-Tenant-ID": tenant.id},
        json=request,
    )
    isolated = client.post(
        f"/assets/{asset.id}/episodes",
        headers={"X-Tenant-ID": other_tenant.id},
        json=request,
    )
    invalid = client.post(
        f"/assets/{asset.id}/episodes",
        headers={"X-Tenant-ID": tenant.id},
        json={**request, "min_similarity": 2},
    )

    assert response.status_code == 201
    assert response.json()["episode_count"] == 1
    assert isolated.status_code == 404
    assert invalid.status_code == 422

    app.dependency_overrides.clear()
