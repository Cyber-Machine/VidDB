from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import TypedDict

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.indexing.embeddings import (
    EmbeddingProvider,
    cosine_similarity,
    default_embedding_provider,
)
from apps.persistence.models import Index, MediaAsset, TemporalRecord


@dataclass(frozen=True)
class SearchRecord:
    asset_id: str
    collection_id: str
    start_ms: int
    end_ms: int
    index_name: str
    index_version: str
    payload: dict[str, object]


@dataclass(frozen=True)
class Candidate:
    asset_id: str
    start_ms: int
    end_ms: int
    modality: str
    evidence: str
    source_frame_uri: str | None
    vector_score: float
    full_text_score: float


class SearchResult(TypedDict):
    asset_id: str
    start_ms: int
    end_ms: int
    score: float
    evidence: list[str]
    modalities: list[str]
    source_frame_uris: list[str]


class SearchResponse(TypedDict):
    results: list[SearchResult]
    next_cursor: str | None


def hybrid_search(
    session: Session,
    tenant_id: str,
    query: str,
    collection_ids: Sequence[str] | None = None,
    asset_ids: Sequence[str] | None = None,
    start_ms: int | None = None,
    end_ms: int | None = None,
    modalities: Sequence[str] | None = None,
    index_versions: Sequence[str] | None = None,
    vector_weight: float = 0.7,
    full_text_weight: float = 0.3,
    pre_roll_ms: int = 0,
    post_roll_ms: int = 0,
    cursor: str | None = None,
    limit: int = 10,
    embedding_provider: EmbeddingProvider | None = None,
) -> SearchResponse:
    records = _load_records(
        session=session,
        tenant_id=tenant_id,
        collection_ids=collection_ids,
        asset_ids=asset_ids,
        start_ms=start_ms,
        end_ms=end_ms,
        modalities=modalities,
        index_versions=index_versions,
    )
    semantic_embeddings = embedding_provider or default_embedding_provider()
    query_embedding = semantic_embeddings.embed_query(query)
    with ThreadPoolExecutor(max_workers=2) as executor:
        vector_future = executor.submit(
            _vector_candidates,
            records,
            query_embedding,
            semantic_embeddings.model_id,
        )
        full_text_future = executor.submit(_full_text_candidates, records, query)
        candidates = vector_future.result() + full_text_future.result()

    weighted = _weighted_candidates(candidates, vector_weight, full_text_weight)
    merged = _merge_overlaps(weighted)
    rolled = [_apply_roll(result, pre_roll_ms, post_roll_ms) for result in merged]
    offset = int(cursor or 0)
    page = rolled[offset : offset + limit]
    next_offset = offset + limit
    next_cursor = str(next_offset) if next_offset < len(rolled) else None
    return {"results": page, "next_cursor": next_cursor}


def _load_records(
    session: Session,
    tenant_id: str,
    collection_ids: Sequence[str] | None,
    asset_ids: Sequence[str] | None,
    start_ms: int | None,
    end_ms: int | None,
    modalities: Sequence[str] | None,
    index_versions: Sequence[str] | None,
) -> list[SearchRecord]:
    statement = (
        select(TemporalRecord, Index, MediaAsset)
        .join(Index, TemporalRecord.index_id == Index.id)
        .join(MediaAsset, TemporalRecord.asset_id == MediaAsset.id)
        .where(TemporalRecord.tenant_id == tenant_id)
    )
    if collection_ids is not None:
        statement = statement.where(MediaAsset.collection_id.in_(collection_ids))
    if asset_ids is not None:
        statement = statement.where(TemporalRecord.asset_id.in_(asset_ids))
    if start_ms is not None:
        statement = statement.where(TemporalRecord.end_ms >= start_ms)
    if end_ms is not None:
        statement = statement.where(TemporalRecord.start_ms <= end_ms)
    if modalities is not None:
        statement = statement.where(Index.name.in_(modalities))
    if index_versions is not None:
        statement = statement.where(Index.version.in_(index_versions))

    return [
        SearchRecord(
            asset_id=record.asset_id,
            collection_id=asset.collection_id,
            start_ms=record.start_ms,
            end_ms=record.end_ms,
            index_name=index.name,
            index_version=index.version,
            payload=record.payload,
        )
        for record, index, asset in session.execute(statement)
    ]


def _vector_candidates(
    records: list[SearchRecord],
    query_embedding: list[float],
    embedding_model: str,
) -> list[Candidate]:
    candidates: list[Candidate] = []
    for record in records:
        embedding = _embedding(record, embedding_model)
        if embedding is None:
            continue
        candidates.append(
            Candidate(
                asset_id=record.asset_id,
                start_ms=record.start_ms,
                end_ms=record.end_ms,
                modality=record.index_name,
                evidence=_evidence(record),
                source_frame_uri=_source_frame_uri(record),
                vector_score=cosine_similarity(query_embedding, embedding),
                full_text_score=0.0,
            )
        )
    return candidates


def _full_text_candidates(
    records: list[SearchRecord],
    query: str,
) -> list[Candidate]:
    lowered_query = query.lower()
    candidates: list[Candidate] = []
    for record in records:
        evidence = _evidence(record)
        if lowered_query not in evidence.lower():
            continue
        candidates.append(
            Candidate(
                asset_id=record.asset_id,
                start_ms=record.start_ms,
                end_ms=record.end_ms,
                modality=record.index_name,
                evidence=evidence,
                source_frame_uri=_source_frame_uri(record),
                vector_score=0.0,
                full_text_score=1.0,
            )
        )
    return candidates


def _weighted_candidates(
    candidates: list[Candidate],
    vector_weight: float,
    full_text_weight: float,
) -> list[SearchResult]:
    max_vector = max((candidate.vector_score for candidate in candidates), default=0.0)
    max_full_text = max(
        (candidate.full_text_score for candidate in candidates),
        default=0.0,
    )
    results: list[SearchResult] = []
    for candidate in candidates:
        vector_score = candidate.vector_score / max_vector if max_vector else 0.0
        full_text_score = (
            candidate.full_text_score / max_full_text if max_full_text else 0.0
        )
        results.append(
            {
                "asset_id": candidate.asset_id,
                "start_ms": candidate.start_ms,
                "end_ms": candidate.end_ms,
                "score": (vector_score * vector_weight)
                + (full_text_score * full_text_weight),
                "evidence": [candidate.evidence],
                "modalities": [candidate.modality],
                "source_frame_uris": (
                    [candidate.source_frame_uri]
                    if candidate.source_frame_uri is not None
                    else []
                ),
            }
        )
    return sorted(results, key=lambda result: result["score"], reverse=True)


def _merge_overlaps(results: list[SearchResult]) -> list[SearchResult]:
    merged: list[SearchResult] = []
    for result in results:
        existing = next(
            (
                item
                for item in merged
                if item["asset_id"] == result["asset_id"]
                and item["start_ms"] <= result["end_ms"]
                and result["start_ms"] <= item["end_ms"]
            ),
            None,
        )
        if existing is None:
            merged.append(result)
            continue
        existing["start_ms"] = min(existing["start_ms"], result["start_ms"])
        existing["end_ms"] = max(existing["end_ms"], result["end_ms"])
        existing["score"] = max(existing["score"], result["score"])
        existing["evidence"] = _unique_strings(
            existing["evidence"] + result["evidence"]
        )
        existing["modalities"] = _ordered_modalities(
            existing["modalities"] + result["modalities"]
        )
        existing["source_frame_uris"] = _unique_strings(
            existing["source_frame_uris"] + result["source_frame_uris"]
        )
    return sorted(merged, key=lambda result: result["score"], reverse=True)


def _apply_roll(
    result: SearchResult,
    pre_roll_ms: int,
    post_roll_ms: int,
) -> SearchResult:
    return {
        "asset_id": result["asset_id"],
        "start_ms": max(0, result["start_ms"] - pre_roll_ms),
        "end_ms": result["end_ms"] + post_roll_ms,
        "score": result["score"],
        "evidence": result["evidence"],
        "modalities": result["modalities"],
        "source_frame_uris": result["source_frame_uris"],
    }


def _evidence(record: SearchRecord) -> str:
    text = record.payload.get("text")
    if isinstance(text, str):
        return text
    description = record.payload.get("description")
    if isinstance(description, str):
        return description
    return ""


def _source_frame_uri(record: SearchRecord) -> str | None:
    value = record.payload.get("source_frame_uri")
    return value if isinstance(value, str) else None


def _embedding(
    record: SearchRecord,
    embedding_model: str,
) -> list[float] | None:
    if record.payload.get("embedding_model") != embedding_model:
        return None
    value = record.payload.get("embedding")
    if not isinstance(value, list):
        return None
    embedding: list[float] = []
    for item in value:
        if not isinstance(item, int | float):
            return None
        embedding.append(float(item))
    return embedding


def _unique_strings(values: list[str]) -> list[str]:
    unique: list[str] = []
    for value in values:
        if value not in unique:
            unique.append(value)
    return unique


def _ordered_modalities(values: list[str]) -> list[str]:
    unique = _unique_strings(values)
    order = {"transcript": 0, "visual": 1, "episode": 2}
    return sorted(unique, key=lambda value: (order.get(value, len(order)), value))
