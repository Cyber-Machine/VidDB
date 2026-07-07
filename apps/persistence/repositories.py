from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.persistence.models import (
    Collection,
    Index,
    Job,
    MediaAsset,
    MediaSegment,
    Rendition,
    TemporalRecord,
    Tenant,
    VirtualClip,
)


class TenantRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, name: str) -> Tenant:
        tenant = Tenant(name=name)
        self.session.add(tenant)
        self.session.flush()
        return tenant


class TenantScopedRepository[
    ModelT: (
        Collection,
        MediaAsset,
        Rendition,
        MediaSegment,
        Index,
        TemporalRecord,
        VirtualClip,
        Job,
    )
]:
    model: type[ModelT]

    def __init__(self, session: Session, tenant_id: str) -> None:
        self.session = session
        self.tenant_id = tenant_id

    def add(self, item: ModelT) -> ModelT:
        item.tenant_id = self.tenant_id
        self.session.add(item)
        self.session.flush()
        return item

    def get(self, item_id: str) -> ModelT | None:
        statement = select(self.model).where(
            self.model.id == item_id,
            self.model.tenant_id == self.tenant_id,
        )
        return self.session.scalar(statement)

    def list(self) -> list[ModelT]:
        statement = select(self.model).where(self.model.tenant_id == self.tenant_id)
        return list(self.session.scalars(statement))


class CollectionRepository(TenantScopedRepository[Collection]):
    model = Collection

    def get_by_name(self, name: str) -> Collection | None:
        statement = select(Collection).where(
            Collection.tenant_id == self.tenant_id,
            Collection.name == name,
        )
        return self.session.scalar(statement)


class MediaAssetRepository(TenantScopedRepository[MediaAsset]):
    model = MediaAsset

    def list_for_collection(self, collection_id: str) -> list[MediaAsset]:
        statement = select(MediaAsset).where(
            MediaAsset.tenant_id == self.tenant_id,
            MediaAsset.collection_id == collection_id,
        )
        return list(self.session.scalars(statement))


class RenditionRepository(TenantScopedRepository[Rendition]):
    model = Rendition

    def get_for_asset_and_kind(self, asset_id: str, kind: str) -> Rendition | None:
        statement = select(Rendition).where(
            Rendition.tenant_id == self.tenant_id,
            Rendition.asset_id == asset_id,
            Rendition.kind == kind,
        )
        return self.session.scalar(statement)


class MediaSegmentRepository(TenantScopedRepository[MediaSegment]):
    model = MediaSegment

    def list_for_asset(self, asset_id: str) -> list[MediaSegment]:
        statement = select(MediaSegment).where(
            MediaSegment.tenant_id == self.tenant_id,
            MediaSegment.asset_id == asset_id,
        )
        return list(self.session.scalars(statement))


class IndexRepository(TenantScopedRepository[Index]):
    model = Index

    def get_by_name_and_version(self, name: str, version: str) -> Index | None:
        statement = select(Index).where(
            Index.tenant_id == self.tenant_id,
            Index.name == name,
            Index.version == version,
        )
        return self.session.scalar(statement)


class TemporalRecordRepository(TenantScopedRepository[TemporalRecord]):
    model = TemporalRecord

    def list_for_index(self, index_id: str) -> list[TemporalRecord]:
        statement = select(TemporalRecord).where(
            TemporalRecord.tenant_id == self.tenant_id,
            TemporalRecord.index_id == index_id,
        )
        return list(self.session.scalars(statement))

    def list_for_asset_and_index(
        self,
        asset_id: str,
        index_id: str,
    ) -> list[TemporalRecord]:
        statement = select(TemporalRecord).where(
            TemporalRecord.tenant_id == self.tenant_id,
            TemporalRecord.asset_id == asset_id,
            TemporalRecord.index_id == index_id,
        )
        return list(self.session.scalars(statement))


class VirtualClipRepository(TenantScopedRepository[VirtualClip]):
    model = VirtualClip


class JobRepository(TenantScopedRepository[Job]):
    model = Job

    def get_by_idempotency_key(self, idempotency_key: str) -> Job | None:
        statement = select(Job).where(
            Job.tenant_id == self.tenant_id,
            Job.idempotency_key == idempotency_key,
        )
        return self.session.scalar(statement)
