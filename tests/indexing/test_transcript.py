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
    assert rebuilt.version == "v2"
    assert transcript_full_text_search(session, tenant.id, index.id, "goal")[0][
        "start_ms"
    ] == 0
    assert transcript_vector_search(session, tenant.id, index.id, "goal")[0][
        "evidence"
    ]
