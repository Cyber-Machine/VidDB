from sqlalchemy.orm import Session

from apps.events import (
    create_event_clip,
    deliver_webhook_alert,
    evaluate_event_rule,
    measure_event_latency,
    stable_event_id,
    store_event_rule,
    websocket_event_payload,
)
from apps.indexing.transcript import MetadataASRProvider, build_transcript_index
from apps.persistence.models import Collection, MediaAsset, MediaSegment
from apps.persistence.repositories import (
    CollectionRepository,
    EventRepository,
    MediaAssetRepository,
    MediaSegmentRepository,
    TemporalRecordRepository,
    TenantRepository,
)


def test_event_rules_alerts_and_event_clips(session: Session) -> None:
    tenant = TenantRepository(session).add("tenant-a")
    collection = CollectionRepository(session, tenant.id).add(Collection(name="games"))
    asset = MediaAssetRepository(session, tenant.id).add(
        MediaAsset(
            collection_id=collection.id,
            source_uri="s3://bucket/game.mp4",
            metadata_={
                "transcript": [
                    {"start_ms": 0, "end_ms": 1000, "text": "goal scored"},
                ]
            },
        )
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
    build_transcript_index(session, tenant.id, asset.id, "v1", MetadataASRProvider())

    rule = store_event_rule(session, tenant.id, "goal-rule", "goal", "https://hook")
    events = evaluate_event_rule(session, tenant.id, rule)
    record = TemporalRecordRepository(session, tenant.id).list()[0]
    alert = deliver_webhook_alert(
        session,
        tenant.id,
        events[0].id,
        "https://hook",
        fail_once=True,
    )
    clip = create_event_clip(session, tenant.id, events[0])

    assert events[0].id == stable_event_id(rule.id, record)
    assert websocket_event_payload(events[0])["event_id"] == events[0].id
    assert alert.status == "delivered"
    assert alert.attempts == 2
    assert clip.manifest["copies_media_bytes"] is False
    assert EventRepository(session, tenant.id).list()
    assert measure_event_latency(session, tenant.id, rule) < 0.05
