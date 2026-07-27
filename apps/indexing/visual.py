from dataclasses import dataclass
from typing import Protocol

from sqlalchemy.orm import Session

from apps.indexing.embeddings import (
    EmbeddingProvider,
    cosine_similarity,
    default_embedding_provider,
)
from apps.persistence.models import Index, ProcessingState, TemporalRecord
from apps.persistence.repositories import (
    IndexRepository,
    MediaAssetRepository,
    MediaSegmentRepository,
    TemporalRecordRepository,
)


@dataclass(frozen=True)
class Shot:
    start_ms: int
    end_ms: int


@dataclass(frozen=True)
class Frame:
    timestamp_ms: int
    uri: str


class VisualModelProvider(Protocol):
    def describe(self, frame: Frame) -> str:
        pass


class DeterministicVisualProvider:
    def describe(self, frame: Frame) -> str:
        return f"representative frame at {frame.timestamp_ms}ms"


def extract_shots(session: Session, tenant_id: str, asset_id: str) -> list[Shot]:
    segments = MediaSegmentRepository(session, tenant_id).list_for_asset(asset_id)
    return [
        Shot(start_ms=segment.start_ms, end_ms=segment.end_ms)
        for segment in segments
    ]


def representative_frames(asset_id: str, shots: list[Shot]) -> list[Frame]:
    return [
        Frame(
            timestamp_ms=shot.start_ms + ((shot.end_ms - shot.start_ms) // 2),
            uri=f"s3://derived/{asset_id}/frames/{index}.jpg",
        )
        for index, shot in enumerate(shots)
    ]


def build_visual_index(
    session: Session,
    tenant_id: str,
    asset_id: str,
    version: str,
    provider: VisualModelProvider,
    embedding_provider: EmbeddingProvider | None = None,
) -> Index:
    asset = MediaAssetRepository(session, tenant_id).get(asset_id)
    if asset is None:
        raise ValueError("asset not found")
    semantic_embeddings = embedding_provider or default_embedding_provider()
    index = _ensure_index(
        session,
        tenant_id,
        "visual",
        version,
        "vision",
        semantic_embeddings.model_id,
    )
    records = TemporalRecordRepository(session, tenant_id)
    existing_records = records.list_for_asset_and_index(asset_id, index.id)
    if existing_records and all(
        record.payload.get("embedding_model") == semantic_embeddings.model_id
        for record in existing_records
    ):
        return index
    for record in existing_records:
        session.delete(record)
    try:
        shots = extract_shots(session, tenant_id, asset_id)
        for shot, frame in zip(shots, representative_frames(asset_id, shots)):
            description = provider.describe(frame)
            records.add(
                TemporalRecord(
                    asset_id=asset_id,
                    index_id=index.id,
                    start_ms=shot.start_ms,
                    end_ms=shot.end_ms,
                    payload={
                        "description": description,
                        "embedding": semantic_embeddings.embed_document(description),
                        "embedding_model": semantic_embeddings.model_id,
                        "source_frame_uri": frame.uri,
                    },
                )
            )
    except Exception:
        asset.processing_state = ProcessingState.PARTIALLY_READY
        session.commit()
        raise
    session.commit()
    return index


def visual_vector_search(
    session: Session,
    tenant_id: str,
    index_id: str,
    query: str,
    embedding_provider: EmbeddingProvider | None = None,
) -> list[dict[str, object]]:
    semantic_embeddings = embedding_provider or default_embedding_provider()
    query_embedding = semantic_embeddings.embed_query(query)
    records = TemporalRecordRepository(session, tenant_id).list_for_index(index_id)
    return sorted(
        [
            {
                "start_ms": record.start_ms,
                "end_ms": record.end_ms,
                "source_frame_uri": record.payload["source_frame_uri"],
                "evidence": record.payload["description"],
                "score": cosine_similarity(
                    query_embedding,
                    record.payload["embedding"],
                ),
            }
            for record in records
            if record.payload.get("embedding_model") == semantic_embeddings.model_id
        ],
        key=lambda result: result["score"],
        reverse=True,
    )


def _ensure_index(
    session: Session,
    tenant_id: str,
    name: str,
    version: str,
    modality: str,
    embedding_model: str,
) -> Index:
    indexes = IndexRepository(session, tenant_id)
    existing = indexes.get_by_name_and_version(name, version)
    if existing is not None:
        existing.metadata_ = {
            **existing.metadata_,
            "embedding_model": embedding_model,
        }
        return existing
    return indexes.add(
        Index(
            name=name,
            version=version,
            modality=modality,
            metadata_={
                "version": version,
                "embedding_model": embedding_model,
            },
        )
    )
