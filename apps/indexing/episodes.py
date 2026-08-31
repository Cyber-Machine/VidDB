from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy.orm import Session

from apps.indexing.embeddings import cosine_similarity
from apps.persistence.models import Index, TemporalRecord
from apps.persistence.repositories import (
    IndexRepository,
    MediaAssetRepository,
    TemporalRecordRepository,
)


@dataclass(frozen=True)
class Episode:
    start_ms: int
    end_ms: int
    record_ids: tuple[str, ...]


def build_episode_index(
    session: Session,
    tenant_id: str,
    asset_id: str,
    source_index_id: str,
    version: str,
    *,
    max_gap_ms: int = 5_000,
    min_similarity: float = 0.65,
) -> Index:
    if MediaAssetRepository(session, tenant_id).get(asset_id) is None:
        raise ValueError("asset not found")
    indexes = IndexRepository(session, tenant_id)
    source_index = indexes.get(source_index_id)
    if source_index is None:
        raise ValueError("source index not found")
    if source_index.name == "episode":
        raise ValueError("an episode index cannot be its own source")

    source_records = TemporalRecordRepository(
        session, tenant_id
    ).list_for_asset_and_index(asset_id, source_index_id)
    if not source_records:
        raise ValueError("source index has no records for asset")
    episodes = detect_episodes(
        source_records,
        max_gap_ms=max_gap_ms,
        min_similarity=min_similarity,
    )
    model_id = _model_id(source_records[0])
    configuration = {
        "source_index_id": source_index.id,
        "source_index_name": source_index.name,
        "source_index_version": source_index.version,
        "embedding_model": model_id,
        "max_gap_ms": max_gap_ms,
        "min_similarity": min_similarity,
    }
    index = indexes.get_by_name_and_version("episode", version)
    if index is not None:
        if index.metadata_ != configuration:
            raise ValueError(
                "episode index version already has different configuration"
            )
        existing = TemporalRecordRepository(
            session, tenant_id
        ).list_for_asset_and_index(asset_id, index.id)
        if existing:
            return index
    else:
        index = indexes.add(
            Index(
                name="episode",
                version=version,
                modality="memory",
                metadata_=configuration,
            )
        )

    by_id = {record.id: record for record in source_records}
    records = TemporalRecordRepository(session, tenant_id)
    for episode in episodes:
        sources = [by_id[record_id] for record_id in episode.record_ids]
        evidence = _evidence(sources)
        payload: dict[str, object] = {
            "text": " ".join(evidence),
            "embedding": _mean_embedding(sources),
            "embedding_model": model_id,
            "source_index_id": source_index.id,
            "source_record_ids": list(episode.record_ids),
            "evidence": evidence,
            "segmentation": {
                "max_gap_ms": max_gap_ms,
                "min_similarity": min_similarity,
            },
        }
        source_frame_uri = _source_frame_uri(sources)
        if source_frame_uri is not None:
            payload["source_frame_uri"] = source_frame_uri
        records.add(
            TemporalRecord(
                asset_id=asset_id,
                index_id=index.id,
                start_ms=episode.start_ms,
                end_ms=episode.end_ms,
                payload=payload,
            )
        )
    session.commit()
    return index


def detect_episodes(
    records: Sequence[TemporalRecord],
    *,
    max_gap_ms: int = 5_000,
    min_similarity: float = 0.65,
) -> list[Episode]:
    """Group one source's adjacent records into semantically coherent episodes."""
    if max_gap_ms < 0:
        raise ValueError("max_gap_ms must be non-negative")
    if not -1.0 <= min_similarity <= 1.0:
        raise ValueError("min_similarity must be between -1 and 1")
    if not records:
        return []

    ordered = sorted(records, key=lambda record: (record.start_ms, record.end_ms))
    identity = _identity(ordered[0])
    model_id = _model_id(ordered[0])
    _embedding(ordered[0])
    current = [ordered[0]]
    episodes: list[Episode] = []

    for record in ordered[1:]:
        if _identity(record) != identity:
            raise ValueError("episode records must share one tenant and source")
        if _model_id(record) != model_id:
            raise ValueError("episode records must share one embedding model")

        previous = current[-1]
        gap_ms = max(0, record.start_ms - previous.end_ms)
        similarity = cosine_similarity(_embedding(previous), _embedding(record))
        if gap_ms > max_gap_ms or similarity < min_similarity:
            episodes.append(_episode(current))
            current = []
        current.append(record)

    episodes.append(_episode(current))
    return episodes


def _identity(record: TemporalRecord) -> tuple[str, str | None, str | None]:
    return record.tenant_id, record.asset_id, record.stream_id


def _model_id(record: TemporalRecord) -> str:
    value = record.payload.get("embedding_model")
    if not isinstance(value, str) or not value:
        raise ValueError("episode records require an embedding model")
    return value


def _embedding(record: TemporalRecord) -> list[float]:
    value = record.payload.get("embedding")
    if not isinstance(value, list) or not value:
        raise ValueError("episode records require embeddings")
    if not all(isinstance(item, int | float) for item in value):
        raise ValueError("episode embeddings must be numeric")
    return [float(item) for item in value]


def _episode(records: list[TemporalRecord]) -> Episode:
    return Episode(
        start_ms=records[0].start_ms,
        end_ms=max(record.end_ms for record in records),
        record_ids=tuple(record.id for record in records),
    )


def _mean_embedding(records: Sequence[TemporalRecord]) -> list[float]:
    embeddings = [_embedding(record) for record in records]
    dimensions = {len(embedding) for embedding in embeddings}
    if len(dimensions) != 1:
        raise ValueError("episode embeddings must have equal dimensions")
    return [
        sum(values) / len(embeddings)
        for values in zip(*embeddings, strict=True)
    ]


def _evidence(records: Sequence[TemporalRecord]) -> list[str]:
    evidence: list[str] = []
    for record in records:
        value = record.payload.get("text", record.payload.get("description"))
        if isinstance(value, str) and value and value not in evidence:
            evidence.append(value)
    return evidence


def _source_frame_uri(records: Sequence[TemporalRecord]) -> str | None:
    for record in records:
        value = record.payload.get("source_frame_uri")
        if isinstance(value, str):
            return value
    return None
