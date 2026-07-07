import uuid
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from apps.persistence.models import Collection, Job, MediaAsset
from apps.persistence.repositories import (
    CollectionRepository,
    JobRepository,
    MediaAssetRepository,
)


def create_collection(session: Session, tenant_id: str, name: str) -> Collection:
    collection = CollectionRepository(session, tenant_id).add(Collection(name=name))
    session.commit()
    return collection


def list_collections(session: Session, tenant_id: str) -> list[Collection]:
    return CollectionRepository(session, tenant_id).list()


def validate_source(source_uri: str, source_type: str) -> None:
    parsed = urlparse(source_uri)
    if source_type == "object" and parsed.scheme not in {"s3", "minio"}:
        raise ValueError("object sources must use s3:// or minio://")
    if source_type == "url" and parsed.scheme not in {"http", "https"}:
        raise ValueError("url sources must use http:// or https://")


def create_asset(
    session: Session,
    tenant_id: str,
    collection_id: str,
    source_uri: str,
    source_type: str = "object",
    idempotency_key: str | None = None,
) -> MediaAsset:
    validate_source(source_uri, source_type)
    assets = MediaAssetRepository(session, tenant_id)
    jobs = JobRepository(session, tenant_id)

    if idempotency_key is not None:
        job = jobs.get_by_idempotency_key(idempotency_key)
        if job is not None:
            asset_id = job.payload["asset_id"]
            asset = assets.get(str(asset_id))
            if asset is None:
                raise ValueError("idempotent asset no longer exists")
            return asset

    asset = assets.add(
        MediaAsset(
            collection_id=collection_id,
            source_uri=source_uri,
            source_type=source_type,
        )
    )
    if idempotency_key is not None:
        jobs.add(
            Job(
                idempotency_key=idempotency_key,
                status="created",
                payload={"asset_id": asset.id},
            )
        )
    session.commit()
    return asset


def get_asset(session: Session, tenant_id: str, asset_id: str) -> MediaAsset | None:
    return MediaAssetRepository(session, tenant_id).get(asset_id)


def create_multipart_upload(
    tenant_id: str,
    collection_id: str,
    filename: str,
    part_count: int,
) -> dict[str, object]:
    upload_id = str(uuid.uuid4())
    object_uri = f"s3://uploads/{tenant_id}/{collection_id}/{upload_id}/{filename}"
    return {
        "upload_id": upload_id,
        "object_uri": object_uri,
        "part_urls": [
            f"http://localhost:9000/uploads/{upload_id}/part/{part_number}"
            for part_number in range(1, part_count + 1)
        ],
    }

