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


def test_search_endpoint_returns_timestamped_evidence(session: Session) -> None:
    tenant = TenantRepository(session).add("tenant-a")
    collection = CollectionRepository(session, tenant.id).add(Collection(name="games"))
    asset = MediaAssetRepository(session, tenant.id).add(
        MediaAsset(
            collection_id=collection.id,
            source_uri="s3://bucket/game.mp4",
            metadata_={
                "transcript": [
                    {"start_ms": 200, "end_ms": 600, "text": "goal scored"},
                ]
            },
        )
    )
    session.commit()
    build_transcript_index(session, tenant.id, asset.id, "v1", MetadataASRProvider())

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_session] = override_session
    client = TestClient(app)
    response = client.post(
        "/search",
        headers={"X-Tenant-ID": tenant.id},
        json={"query": "goal", "modalities": ["transcript"]},
    )

    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["asset_id"] == asset.id
    assert result["start_ms"] == 200
    assert result["end_ms"] == 600
    assert result["evidence"] == ["goal scored"]

    app.dependency_overrides.clear()
