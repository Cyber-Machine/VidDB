from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from apps.api.main import app, get_session
from apps.clips import render_compilation_manifest
from apps.persistence.models import Collection, MediaAsset, MediaSegment
from apps.persistence.repositories import (
    CollectionRepository,
    MediaAssetRepository,
    MediaSegmentRepository,
    TenantRepository,
)


def test_clip_creation_uses_existing_segments_without_copying_bytes(
    session: Session,
) -> None:
    tenant = TenantRepository(session).add("tenant-a")
    collection = CollectionRepository(session, tenant.id).add(Collection(name="games"))
    asset = MediaAssetRepository(session, tenant.id).add(
        MediaAsset(collection_id=collection.id, source_uri="s3://bucket/game.mp4")
    )
    segment = MediaSegmentRepository(session, tenant.id).add(
        MediaSegment(
            asset_id=asset.id,
            start_ms=0,
            end_ms=1000,
            object_uri="s3://derived/game/segment-0.m4s",
        )
    )
    session.commit()

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_session] = override_session
    client = TestClient(app)
    response = client.post(
        "/clips",
        headers={"X-Tenant-ID": tenant.id},
        json={
            "name": "goal",
            "segments": [{"asset_id": asset.id, "start_ms": 0, "end_ms": 500}],
        },
    )

    assert response.status_code == 201
    clip = response.json()
    assert clip["manifest"]["copies_media_bytes"] is False
    assert clip["manifest"]["segments"][0]["segment_id"] == segment.id

    manifest_response = client.get(
        f"/clips/{clip['id']}/manifest",
        headers={"X-Tenant-ID": tenant.id},
    )
    assert manifest_response.status_code == 200
    assert "s3://derived/game/segment-0.m4s" in manifest_response.json()["manifest"]
    assert "token=" in manifest_response.json()["playback_url"]
    assert "s3://derived/game/segment-0.m4s" in render_compilation_manifest(
        session,
        tenant.id,
        [clip["id"]],
    )

    app.dependency_overrides.clear()
