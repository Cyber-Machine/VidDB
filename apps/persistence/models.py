import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, Enum, ForeignKey, UniqueConstraint
from sqlalchemy import Index as SqlIndex
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def new_id() -> str:
    return str(uuid.uuid4())


def now_utc() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class ProcessingState(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    READY = "READY"
    PARTIALLY_READY = "PARTIALLY_READY"
    FAILED = "FAILED"
    DELETED = "DELETED"


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(unique=True)
    created_at: Mapped[datetime] = mapped_column(default=now_utc)

    collections: Mapped[list["Collection"]] = relationship(back_populates="tenant")


class Collection(Base):
    __tablename__ = "collections"
    __table_args__ = (UniqueConstraint("tenant_id", "name"),)

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    name: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(default=now_utc)

    tenant: Mapped[Tenant] = relationship(back_populates="collections")
    assets: Mapped[list["MediaAsset"]] = relationship(back_populates="collection")


class MediaAsset(Base):
    __tablename__ = "media_assets"

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    collection_id: Mapped[str] = mapped_column(ForeignKey("collections.id"), index=True)
    source_uri: Mapped[str]
    source_type: Mapped[str] = mapped_column(default="object")
    processing_state: Mapped[ProcessingState] = mapped_column(
        Enum(ProcessingState),
        default=ProcessingState.PENDING,
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=now_utc)

    collection: Mapped[Collection] = relationship(back_populates="assets")
    renditions: Mapped[list["Rendition"]] = relationship(back_populates="asset")
    segments: Mapped[list["MediaSegment"]] = relationship(back_populates="asset")
    temporal_records: Mapped[list["TemporalRecord"]] = relationship(
        back_populates="asset"
    )


class Rendition(Base):
    __tablename__ = "renditions"

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    asset_id: Mapped[str] = mapped_column(ForeignKey("media_assets.id"), index=True)
    kind: Mapped[str]
    object_uri: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(default=now_utc)

    asset: Mapped[MediaAsset] = relationship(back_populates="renditions")


class MediaSegment(Base):
    __tablename__ = "media_segments"

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    asset_id: Mapped[str] = mapped_column(ForeignKey("media_assets.id"), index=True)
    start_ms: Mapped[int]
    end_ms: Mapped[int]
    object_uri: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(default=now_utc)

    asset: Mapped[MediaAsset] = relationship(back_populates="segments")


class Index(Base):
    __tablename__ = "indexes"
    __table_args__ = (UniqueConstraint("tenant_id", "name", "version"),)

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    name: Mapped[str]
    version: Mapped[str]
    modality: Mapped[str]
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=now_utc)

    temporal_records: Mapped[list["TemporalRecord"]] = relationship(
        back_populates="index"
    )


class TemporalRecord(Base):
    __tablename__ = "temporal_records"

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    asset_id: Mapped[str] = mapped_column(ForeignKey("media_assets.id"), index=True)
    index_id: Mapped[str] = mapped_column(ForeignKey("indexes.id"), index=True)
    start_ms: Mapped[int]
    end_ms: Mapped[int]
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=now_utc)

    asset: Mapped[MediaAsset] = relationship(back_populates="temporal_records")
    index: Mapped[Index] = relationship(back_populates="temporal_records")


class VirtualClip(Base):
    __tablename__ = "virtual_clips"

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    name: Mapped[str]
    manifest: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=now_utc)


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key"),
        SqlIndex("ix_jobs_tenant_status", "tenant_id", "status"),
    )

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    idempotency_key: Mapped[str]
    status: Mapped[str]
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=now_utc)
