from dataclasses import dataclass
from typing import Protocol

from sqlalchemy.orm import Session

from apps.indexing.common import cosine_score, text_embedding
from apps.persistence.models import Index, MediaAsset, TemporalRecord
from apps.persistence.repositories import (
    IndexRepository,
    MediaAssetRepository,
    TemporalRecordRepository,
)


@dataclass(frozen=True)
class Utterance:
    start_ms: int
    end_ms: int
    text: str


class ASRProvider(Protocol):
    def transcribe(self, asset: MediaAsset) -> list[Utterance]:
        pass


class MetadataASRProvider:
    def transcribe(self, asset: MediaAsset) -> list[Utterance]:
        transcript = asset.metadata_.get("transcript")
        if isinstance(transcript, list):
            return [
                Utterance(
                    start_ms=int(item["start_ms"]),
                    end_ms=int(item["end_ms"]),
                    text=str(item["text"]),
                )
                for item in transcript
            ]
        return [Utterance(start_ms=0, end_ms=1000, text=asset.source_uri)]


def build_transcript_index(
    session: Session,
    tenant_id: str,
    asset_id: str,
    version: str,
    provider: ASRProvider,
) -> Index:
    asset = MediaAssetRepository(session, tenant_id).get(asset_id)
    if asset is None:
        raise ValueError("asset not found")
    index = _ensure_index(session, tenant_id, "transcript", version, "text")
    records = TemporalRecordRepository(session, tenant_id)
    if records.list_for_asset_and_index(asset_id, index.id):
        return index
    for utterance in provider.transcribe(asset):
        records.add(
            TemporalRecord(
                asset_id=asset.id,
                index_id=index.id,
                start_ms=utterance.start_ms,
                end_ms=utterance.end_ms,
                payload={
                    "text": utterance.text,
                    "embedding": text_embedding(utterance.text),
                },
            )
        )
    session.commit()
    return index


def transcript_vector_search(
    session: Session,
    tenant_id: str,
    index_id: str,
    query: str,
) -> list[dict[str, object]]:
    query_embedding = text_embedding(query)
    records = TemporalRecordRepository(session, tenant_id).list_for_index(index_id)
    return sorted(
        [
            {
                "start_ms": record.start_ms,
                "end_ms": record.end_ms,
                "evidence": record.payload["text"],
                "score": cosine_score(query_embedding, record.payload["embedding"]),
            }
            for record in records
        ],
        key=lambda result: result["score"],
        reverse=True,
    )


def transcript_full_text_search(
    session: Session,
    tenant_id: str,
    index_id: str,
    query: str,
) -> list[dict[str, object]]:
    records = TemporalRecordRepository(session, tenant_id).list_for_index(index_id)
    return [
        {
            "start_ms": record.start_ms,
            "end_ms": record.end_ms,
            "evidence": record.payload["text"],
        }
        for record in records
        if query.lower() in str(record.payload["text"]).lower()
    ]


def _ensure_index(
    session: Session,
    tenant_id: str,
    name: str,
    version: str,
    modality: str,
) -> Index:
    indexes = IndexRepository(session, tenant_id)
    existing = indexes.get_by_name_and_version(name, version)
    if existing is not None:
        return existing
    return indexes.add(
        Index(
            name=name,
            version=version,
            modality=modality,
            metadata_={"version": version},
        )
    )
