from sqlalchemy.orm import Session

from apps.indexing.transcript import (
    MetadataASRProvider,
    build_transcript_index,
    transcript_full_text_search,
    transcript_vector_search,
)
from apps.persistence.models import Collection, MediaAsset
from apps.persistence.repositories import (
    CollectionRepository,
    MediaAssetRepository,
    TemporalRecordRepository,
    TenantRepository,
)


def test_transcript_index_persists_searchable_temporal_records(
    session: Session,
) -> None:
    tenant = TenantRepository(session).add("tenant-a")
    collection = CollectionRepository(session, tenant.id).add(Collection(name="games"))
    asset = MediaAssetRepository(session, tenant.id).add(
        MediaAsset(
            collection_id=collection.id,
            source_uri="s3://bucket/game.mp4",
            metadata_={
                "transcript": [
                    {"start_ms": 0, "end_ms": 500, "text": "first goal"},
                    {"start_ms": 500, "end_ms": 900, "text": "crowd replay"},
                ]
            },
        )
    )
    session.commit()

    index = build_transcript_index(
        session,
        tenant.id,
        asset.id,
        "v1",
        MetadataASRProvider(),
    )
    rebuilt = build_transcript_index(
        session,
        tenant.id,
        asset.id,
        "v2",
        MetadataASRProvider(),
    )

    records = TemporalRecordRepository(session, tenant.id).list_for_index(index.id)
    assert len(records) == 2
    assert records[0].payload["embedding_model"] == "test-semantic-embedding-v1"
    assert index.metadata_["embedding_model"] == "test-semantic-embedding-v1"
    assert rebuilt.version == "v2"
    assert transcript_full_text_search(session, tenant.id, index.id, "goal")[0][
        "start_ms"
    ] == 0
    assert transcript_vector_search(session, tenant.id, index.id, "goal")[0][
        "evidence"
    ]


def test_transcript_index_replaces_stale_embeddings(session: Session) -> None:
    tenant = TenantRepository(session).add("tenant-a")
    collection = CollectionRepository(session, tenant.id).add(Collection(name="games"))
    asset = MediaAssetRepository(session, tenant.id).add(
        MediaAsset(
            collection_id=collection.id,
            source_uri="s3://bucket/game.mp4",
            metadata_={
                "transcript": [
                    {"start_ms": 0, "end_ms": 500, "text": "first goal"},
                ]
            },
        )
    )
    session.commit()
    index = build_transcript_index(
        session,
        tenant.id,
        asset.id,
        "v1",
        MetadataASRProvider(),
    )
    stale_record = TemporalRecordRepository(
        session,
        tenant.id,
    ).list_for_index(index.id)[0]
    stale_record.payload = {
        **stale_record.payload,
        "embedding": [0.25, 0.25, 0.25, 0.25],
    }
    stale_record.payload.pop("embedding_model")
    session.commit()

    build_transcript_index(
        session,
        tenant.id,
        asset.id,
        "v1",
        MetadataASRProvider(),
    )

    rebuilt_record = TemporalRecordRepository(
        session,
        tenant.id,
    ).list_for_index(index.id)[0]
    assert rebuilt_record.id != stale_record.id
    assert rebuilt_record.payload["embedding_model"] == "test-semantic-embedding-v1"
