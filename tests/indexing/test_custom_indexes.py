from sqlalchemy.orm import Session

from apps.custom_indexes import (
    create_custom_index,
    evaluate_index,
    news_topic_boundary_output,
    promote_alias,
    prompt_hash,
    rebuild_custom_index,
    replay_detection_output,
    scoreboard_change_output,
    speaker_tracking_output,
    validate_structured_output,
)
from apps.persistence.models import Collection, MediaAsset, MediaSegment
from apps.persistence.repositories import (
    CollectionRepository,
    MediaAssetRepository,
    MediaSegmentRepository,
    TenantRepository,
)


def test_custom_index_lifecycle_reuses_frames_and_validates_outputs(
    session: Session,
) -> None:
    tenant = TenantRepository(session).add("tenant-a")
    collection = CollectionRepository(session, tenant.id).add(Collection(name="games"))
    asset = MediaAssetRepository(session, tenant.id).add(
        MediaAsset(collection_id=collection.id, source_uri="s3://bucket/game.mp4")
    )
    MediaSegmentRepository(session, tenant.id).add(
        MediaSegment(
            asset_id=asset.id,
            start_ms=0,
            end_ms=1000,
            object_uri="s3://segment",
        )
    )
    session.commit()

    index = create_custom_index(
        session,
        tenant.id,
        "scoreboard",
        "detect scoreboard changes",
        "deterministic",
        {"temperature": 0},
    )
    promote_alias(index)
    records = rebuild_custom_index(session, tenant.id, asset.id, index.id, "scoreboard")
    result = evaluate_index(session, tenant.id, index.id)

    assert index.metadata_["prompt_hash"] == prompt_hash("detect scoreboard changes")
    assert index.metadata_["alias"] == "production"
    assert records[0].payload["source_frame_uri"]
    assert result.passed
    assert validate_structured_output(scoreboard_change_output("0-0", "1-0"))
    assert validate_structured_output(replay_detection_output(True))
    assert validate_structured_output(speaker_tracking_output("announcer"))
    assert validate_structured_output(news_topic_boundary_output(True))
