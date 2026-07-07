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


class MediaAssetRepository(TenantScopedRepository[MediaAsset]):
    model = MediaAsset


class RenditionRepository(TenantScopedRepository[Rendition]):
    model = Rendition


class MediaSegmentRepository(TenantScopedRepository[MediaSegment]):
    model = MediaSegment


class IndexRepository(TenantScopedRepository[Index]):
    model = Index


class TemporalRecordRepository(TenantScopedRepository[TemporalRecord]):
    model = TemporalRecord


class VirtualClipRepository(TenantScopedRepository[VirtualClip]):
    model = VirtualClip


class JobRepository(TenantScopedRepository[Job]):
    model = Job
