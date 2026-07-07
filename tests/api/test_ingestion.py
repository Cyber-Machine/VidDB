from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from apps.api.main import app, get_session
from apps.persistence.repositories import TenantRepository


def test_collection_and_asset_ingestion_endpoints(session: Session) -> None:
    tenant = TenantRepository(session).add("tenant-a")
    session.commit()

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_session] = override_session
    client = TestClient(app)
    headers = {"X-Tenant-ID": tenant.id, "Idempotency-Key": "asset-1"}

    collection_response = client.post(
        "/collections",
        headers={"X-Tenant-ID": tenant.id},
        json={"name": "games"},
    )
    assert collection_response.status_code == 201
    collection_id = collection_response.json()["id"]

    assert client.get("/collections", headers={"X-Tenant-ID": tenant.id}).json() == [
        {"id": collection_id, "name": "games"}
    ]

    asset_response = client.post(
        "/assets",
        headers=headers,
        json={
            "collection_id": collection_id,
            "source_uri": "s3://bucket/game.mp4",
            "source_type": "object",
        },
    )
    assert asset_response.status_code == 201
    asset = asset_response.json()

    repeat_response = client.post(
        "/assets",
        headers=headers,
        json={
            "collection_id": collection_id,
            "source_uri": "s3://bucket/game.mp4",
            "source_type": "object",
        },
    )
    assert repeat_response.json()["id"] == asset["id"]

    fetched = client.get(f"/assets/{asset['id']}", headers={"X-Tenant-ID": tenant.id})
    assert fetched.json()["source_uri"] == "s3://bucket/game.mp4"

    status = client.get(
        f"/assets/{asset['id']}/status",
        headers={"X-Tenant-ID": tenant.id},
    )
    assert status.json() == {"status": "PENDING"}

    app.dependency_overrides.clear()


def test_upload_contract_and_url_source_validation(session: Session) -> None:
    tenant = TenantRepository(session).add("tenant-a")
    session.commit()

    def override_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_session] = override_session
    client = TestClient(app)

    upload = client.post(
        "/uploads/multipart",
        headers={"X-Tenant-ID": tenant.id},
        json={"collection_id": "collection-a", "filename": "clip.mp4", "part_count": 2},
    )
    assert upload.status_code == 201
    assert len(upload.json()["part_urls"]) == 2

    invalid = client.post(
        "/assets",
        headers={"X-Tenant-ID": tenant.id},
        json={
            "collection_id": "collection-a",
            "source_uri": "ftp://example.com/clip.mp4",
            "source_type": "url",
        },
    )
    assert invalid.status_code == 400

    app.dependency_overrides.clear()
