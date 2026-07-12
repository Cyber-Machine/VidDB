from sqlalchemy.orm import Session

from apps.live import (
    ingest_rtmp,
    ingest_rtsp,
    normalize_live_timestamp,
    publish_inference_windows,
    reconnect_stream,
    rolling_buffer,
    write_live_segment,
    write_live_temporal_record,
)
from apps.persistence.repositories import TenantRepository


def test_live_stream_ingest_buffer_records_and_reconnect(session: Session) -> None:
    tenant = TenantRepository(session).add("tenant-a")
    rtsp = ingest_rtsp(session, tenant.id, "rtsp://camera")
    rtmp = ingest_rtmp(session, tenant.id, "rtmp://encoder")

    assert rtsp.protocol == "rtsp"
    assert rtmp.protocol == "rtmp"
    assert normalize_live_timestamp(1000, 250) == 1250

    first = write_live_segment(session, tenant.id, rtsp.id, 1, 0, 1000)
    duplicate = write_live_segment(session, tenant.id, rtsp.id, 1, 0, 1000)
    write_live_segment(session, tenant.id, rtsp.id, 2, 1000, 2000)
    write_live_segment(session, tenant.id, rtsp.id, 3, 2000, 3000)
    write_live_segment(session, tenant.id, rtsp.id, 4, 3000, 4000)
    record = write_live_temporal_record(session, tenant.id, rtsp.id, 0, 1000, "motion")

    assert duplicate.id == first.id
    sequences = [
        segment.sequence for segment in rolling_buffer(session, tenant.id, rtsp.id)
    ]
    assert sequences == [2, 3, 4]
    assert publish_inference_windows(session, tenant.id, rtsp.id)[-1]["end_ms"] == 4000
    assert record.payload["label"] == "motion"

    reconnected = reconnect_stream(session, tenant.id, rtsp.id)
    next_segment = write_live_segment(session, tenant.id, rtsp.id, 1, 4000, 5000)
    assert reconnected.reconnect_generation == 1
    assert next_segment.generation == 1
