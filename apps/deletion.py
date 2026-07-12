from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.persistence.models import (
    AuditRecord,
    MediaSegment,
    ProcessingState,
    Rendition,
    TemporalRecord,
)
from apps.persistence.repositories import AuditRecordRepository, MediaAssetRepository


def delete_asset(session: Session, tenant_id: str, asset_id: str) -> dict[str, object]:
    asset = MediaAssetRepository(session, tenant_id).get(asset_id)
    if asset is None:
        raise ValueError("asset not found")

    deleted_objects = _derived_object_uris(session, tenant_id, asset_id)
    if asset.source_uri not in deleted_objects:
        deleted_objects.append(asset.source_uri)

    _delete_rows(session, tenant_id, asset_id, TemporalRecord)
    _delete_rows(session, tenant_id, asset_id, Rendition)
    _delete_rows(session, tenant_id, asset_id, MediaSegment)

    asset.processing_state = ProcessingState.DELETED
    asset.metadata_ = {
        **asset.metadata_,
        "tombstone": True,
        "deletion_status": "complete",
        "deleted_objects": deleted_objects,
    }
    AuditRecordRepository(session, tenant_id).add(
        AuditRecord(
            action="asset.deleted",
            subject_id=asset_id,
            payload={"deleted_objects": deleted_objects},
        )
    )
    session.commit()
    return asset_deletion_status(session, tenant_id, asset_id)


def asset_deletion_status(
    session: Session,
    tenant_id: str,
    asset_id: str,
) -> dict[str, object]:
    asset = MediaAssetRepository(session, tenant_id).get(asset_id)
    if asset is None:
        return {"asset_id": asset_id, "status": "not_found", "deleted_objects": []}
    return {
        "asset_id": asset_id,
        "status": str(asset.metadata_.get("deletion_status", "not_started")),
        "deleted_objects": list(asset.metadata_.get("deleted_objects", [])),
    }


def _derived_object_uris(
    session: Session,
    tenant_id: str,
    asset_id: str,
) -> list[str]:
    rendition_uris = [
        row.object_uri
        for row in session.scalars(
            select(Rendition).where(
                Rendition.tenant_id == tenant_id,
                Rendition.asset_id == asset_id,
            )
        )
    ]
    segment_uris = [
        row.object_uri
        for row in session.scalars(
            select(MediaSegment).where(
                MediaSegment.tenant_id == tenant_id,
                MediaSegment.asset_id == asset_id,
            )
        )
    ]
    return rendition_uris + segment_uris


def _delete_rows(
    session: Session,
    tenant_id: str,
    asset_id: str,
    model: type[TemporalRecord] | type[Rendition] | type[MediaSegment],
) -> None:
    for row in session.scalars(
        select(model).where(
            model.tenant_id == tenant_id,
            model.asset_id == asset_id,
        )
    ):
        session.delete(row)
