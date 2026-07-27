from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from apps.persistence.models import Index, LiveSegment, RTStream, TemporalRecord
from apps.persistence.repositories import (
    IndexRepository,
    LiveSegmentRepository,
    RTStreamRepository,
    TemporalRecordRepository,
)

ROLLING_BUFFER_SIZE = 3


def ingest_rtsp(session: Session, tenant_id: str, source_uri: str) -> RTStream:
    return _create_stream(session, tenant_id, source_uri, "rtsp")


def ingest_rtmp(session: Session, tenant_id: str, source_uri: str) -> RTStream:
    return _create_stream(session, tenant_id, source_uri, "rtmp")


def normalize_live_timestamp(base_ms: int, offset_ms: int) -> int:
    return base_ms + offset_ms


def write_live_segment(
    session: Session,
    tenant_id: str,
    stream_id: str,
    sequence: int,
    start_ms: int,
    end_ms: int,
) -> LiveSegment:
    stream = RTStreamRepository(session, tenant_id).get(stream_id)
    if stream is None:
        raise ValueError("stream not found")
    repository = LiveSegmentRepository(session, tenant_id)
    segment = LiveSegment(
        stream_id=stream_id,
        generation=stream.reconnect_generation,
        sequence=sequence,
        start_ms=start_ms,
        end_ms=end_ms,
        object_uri=f"s3://live/{stream_id}/{stream.reconnect_generation}/{sequence}.m4s",
    )
    try:
        repository.add(segment)
        stream.watermark_ms = max(stream.watermark_ms, end_ms)
        session.commit()
        return segment
    except IntegrityError:
        session.rollback()
        existing = [
            item
            for item in repository.list_for_stream(stream_id)
            if item.generation == stream.reconnect_generation
            and item.sequence == sequence
        ]
        return existing[0]


def rolling_buffer(
    session: Session,
    tenant_id: str,
    stream_id: str,
) -> list[LiveSegment]:
    segments = LiveSegmentRepository(session, tenant_id).list_for_stream(stream_id)
    return sorted(segments, key=lambda segment: segment.sequence)[-ROLLING_BUFFER_SIZE:]


def publish_inference_windows(
    session: Session,
    tenant_id: str,
    stream_id: str,
) -> list[dict[str, int]]:
    return [
        {"start_ms": segment.start_ms, "end_ms": segment.end_ms}
        for segment in rolling_buffer(session, tenant_id, stream_id)
    ]


def write_live_temporal_record(
    session: Session,
    tenant_id: str,
    stream_id: str,
    start_ms: int,
    end_ms: int,
    label: str,
) -> TemporalRecord:
    index = _live_index(session, tenant_id)
    record = TemporalRecordRepository(session, tenant_id).add(
        TemporalRecord(
            stream_id=stream_id,
            index_id=index.id,
            start_ms=start_ms,
            end_ms=end_ms,
            payload={"label": label, "stream_id": stream_id},
        )
    )
    session.commit()
    return record


def reconnect_stream(session: Session, tenant_id: str, stream_id: str) -> RTStream:
    stream = RTStreamRepository(session, tenant_id).get(stream_id)
    if stream is None:
        raise ValueError("stream not found")
    stream.reconnect_generation += 1
    session.commit()
    return stream


def _create_stream(
    session: Session,
    tenant_id: str,
    source_uri: str,
    protocol: str,
) -> RTStream:
    stream = RTStreamRepository(session, tenant_id).add(
        RTStream(source_uri=source_uri, protocol=protocol)
    )
    session.commit()
    return stream


def _live_index(session: Session, tenant_id: str) -> Index:
    indexes = IndexRepository(session, tenant_id)
    existing = indexes.get_by_name_and_version("live", "v1")
    if existing is not None:
        return existing
    return indexes.add(Index(name="live", version="v1", modality="live"))
