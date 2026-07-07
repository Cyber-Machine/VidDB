from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from apps.persistence.migrations import run_migrations
from apps.persistence.models import (
    Collection,
    Index,
    Job,
    MediaAsset,
    MediaSegment,
    Rendition,
    TemporalRecord,
    VirtualClip,
)
from apps.persistence.repositories import (
    CollectionRepository,
    IndexRepository,
    JobRepository,
    MediaAssetRepository,
    MediaSegmentRepository,
    RenditionRepository,
    TemporalRecordRepository,
    TenantRepository,
    VirtualClipRepository,
)


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:")
    run_migrations(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory() as session:
        yield session


def test_collection_repository_queries_exclude_other_tenant_rows(
    session: Session,
) -> None:
    tenants = TenantRepository(session)
    tenant = tenants.add("tenant-a")
    other_tenant = tenants.add("tenant-b")

    tenant_collections = CollectionRepository(session, tenant.id)
    other_collections = CollectionRepository(session, other_tenant.id)
    collection = tenant_collections.add(Collection(name="collection-a"))
    other_collection = other_collections.add(Collection(name="collection-b"))

    assert tenant_collections.get(collection.id) == collection
    assert tenant_collections.get(other_collection.id) is None
    assert tenant_collections.list() == [collection]


def test_each_domain_repository_applies_tenant_scope(session: Session) -> None:
    tenants = TenantRepository(session)
    tenant = tenants.add("tenant-a")
    other_tenant = tenants.add("tenant-b")

    collections = CollectionRepository(session, tenant.id)
    collection = collections.add(Collection(name="collection-a"))
    other_collection = CollectionRepository(session, other_tenant.id).add(
        Collection(name="collection-b")
    )

    assets = MediaAssetRepository(session, tenant.id)
    asset = assets.add(MediaAsset(collection_id=collection.id, source_uri="s3://asset-a"))
    other_asset = MediaAssetRepository(session, other_tenant.id).add(
        MediaAsset(collection_id=other_collection.id, source_uri="s3://asset-b")
    )

    index = IndexRepository(session, tenant.id).add(
        Index(name="transcript", version="v1", modality="text")
    )
    other_index = IndexRepository(session, other_tenant.id).add(
        Index(name="transcript", version="v1", modality="text")
    )

    renditions = RenditionRepository(session, tenant.id)
    rendition = renditions.add(
        Rendition(asset_id=asset.id, kind="proxy", object_uri="s3://proxy-a")
    )
    RenditionRepository(session, other_tenant.id).add(
        Rendition(asset_id=other_asset.id, kind="proxy", object_uri="s3://proxy-b")
    )
    assert renditions.get(rendition.id) == rendition
    assert RenditionRepository(session, other_tenant.id).get(rendition.id) is None

    segments = MediaSegmentRepository(session, tenant.id)
    segment = segments.add(
        MediaSegment(
            asset_id=asset.id,
            start_ms=0,
            end_ms=1000,
            object_uri="s3://segment-a",
        )
    )
    MediaSegmentRepository(session, other_tenant.id).add(
        MediaSegment(
            asset_id=other_asset.id,
            start_ms=0,
            end_ms=1000,
            object_uri="s3://segment-b",
        )
    )
    assert segments.get(segment.id) == segment
    assert MediaSegmentRepository(session, other_tenant.id).get(segment.id) is None

    records = TemporalRecordRepository(session, tenant.id)
    record = records.add(
        TemporalRecord(asset_id=asset.id, index_id=index.id, start_ms=0, end_ms=1000)
    )
    TemporalRecordRepository(session, other_tenant.id).add(
        TemporalRecord(
            asset_id=other_asset.id,
            index_id=other_index.id,
            start_ms=0,
            end_ms=1000,
        )
    )
    assert records.get(record.id) == record
    assert TemporalRecordRepository(session, other_tenant.id).get(record.id) is None

    clips = VirtualClipRepository(session, tenant.id)
    clip = clips.add(VirtualClip(name="clip-a"))
    VirtualClipRepository(session, other_tenant.id).add(VirtualClip(name="clip-b"))
    assert clips.get(clip.id) == clip
    assert VirtualClipRepository(session, other_tenant.id).get(clip.id) is None

    jobs = JobRepository(session, tenant.id)
    job = jobs.add(Job(idempotency_key="job-a", status="pending"))
    JobRepository(session, other_tenant.id).add(
        Job(idempotency_key="job-b", status="pending")
    )
    assert jobs.get(job.id) == job
    assert JobRepository(session, other_tenant.id).get(job.id) is None
