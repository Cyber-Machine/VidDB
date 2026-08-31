import pytest
from sqlalchemy.orm import Session

from apps.indexing.episodes import build_episode_index, detect_episodes
from apps.indexing.transcript import MetadataASRProvider, build_transcript_index
from apps.persistence.models import Collection, MediaAsset, TemporalRecord
from apps.persistence.repositories import (
    CollectionRepository,
    MediaAssetRepository,
    TemporalRecordRepository,
    TenantRepository,
)
from apps.search import hybrid_search


def test_detect_episodes_splits_on_semantic_change_and_time_gap() -> None:
    records = [
        _record("crowd", 900, 1_400, [1.0, 0.1]),
        _record("play", 0, 800, [1.0, 0.0]),
        _record("interview", 1_500, 2_000, [0.0, 1.0]),
        _record("later", 8_000, 8_500, [0.0, 1.0]),
    ]

    episodes = detect_episodes(records, max_gap_ms=1_000, min_similarity=0.8)

    assert [(episode.start_ms, episode.end_ms) for episode in episodes] == [
        (0, 1_400),
        (1_500, 2_000),
        (8_000, 8_500),
    ]
    assert episodes[0].record_ids == ("play", "crowd")


def test_episode_index_persists_searchable_provenance(session: Session) -> None:
    tenant = TenantRepository(session).add("tenant-a")
    collection = CollectionRepository(session, tenant.id).add(Collection(name="games"))
    asset = MediaAssetRepository(session, tenant.id).add(
        MediaAsset(
            collection_id=collection.id,
            source_uri="s3://bucket/game.mp4",
            metadata_={
                "transcript": [
                    {"start_ms": 0, "end_ms": 500, "text": "goal scored"},
                    {"start_ms": 600, "end_ms": 1_000, "text": "ball in net"},
                    {"start_ms": 1_100, "end_ms": 1_500, "text": "crowd cheers"},
                ]
            },
        )
    )
    session.commit()
    source = build_transcript_index(
        session, tenant.id, asset.id, "v1", MetadataASRProvider()
    )

    index = build_episode_index(
        session,
        tenant.id,
        asset.id,
        source.id,
        "transcript-v1",
        min_similarity=0.8,
    )
    rebuilt = build_episode_index(
        session,
        tenant.id,
        asset.id,
        source.id,
        "transcript-v1",
        min_similarity=0.8,
    )
    records = TemporalRecordRepository(
        session, tenant.id
    ).list_for_asset_and_index(asset.id, index.id)
    results = hybrid_search(
        session,
        tenant.id,
        "goal",
        modalities=["episode"],
        embedding_provider=_TestEmbeddingProvider(),
    )["results"]

    assert rebuilt.id == index.id
    assert len(records) == 2
    assert records[0].payload["source_record_ids"]
    assert records[0].payload["segmentation"] == {
        "max_gap_ms": 5_000,
        "min_similarity": 0.8,
    }
    assert results[0]["start_ms"] == 0
    assert results[0]["end_ms"] == 1_000
    assert results[0]["modalities"] == ["episode"]

    with pytest.raises(ValueError, match="different configuration"):
        build_episode_index(
            session,
            tenant.id,
            asset.id,
            source.id,
            "transcript-v1",
            min_similarity=0.5,
        )


def _record(
    record_id: str,
    start_ms: int,
    end_ms: int,
    embedding: list[float],
) -> TemporalRecord:
    return TemporalRecord(
        id=record_id,
        tenant_id="tenant-a",
        asset_id="asset-a",
        stream_id=None,
        index_id="visual-v1",
        start_ms=start_ms,
        end_ms=end_ms,
        payload={
            "embedding": embedding,
            "embedding_model": "test-semantic-embedding-v1",
        },
    )


class _TestEmbeddingProvider:
    model_id = "test-semantic-embedding-v1"

    def embed_query(self, text: str) -> list[float]:
        del text
        return [1.0, 0.0, 0.0, 1.0]

    def embed_document(self, text: str) -> list[float]:
        return self.embed_query(text)
