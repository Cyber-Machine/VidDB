import hashlib
from dataclasses import dataclass

from sqlalchemy.orm import Session

from apps.indexing.visual import extract_shots, representative_frames
from apps.persistence.models import Index, TemporalRecord
from apps.persistence.repositories import (
    IndexRepository,
    MediaAssetRepository,
    TemporalRecordRepository,
)


@dataclass(frozen=True)
class EvaluationResult:
    index_id: str
    record_count: int
    passed: bool


def create_custom_index(
    session: Session,
    tenant_id: str,
    name: str,
    prompt: str,
    model: str,
    sampling: dict[str, object],
    version: str = "v1",
) -> Index:
    index = IndexRepository(session, tenant_id).add(
        Index(
            name=name,
            version=version,
            modality="custom",
            metadata_={
                "prompt": prompt,
                "prompt_hash": prompt_hash(prompt),
                "model": model,
                "sampling": sampling,
            },
        )
    )
    session.commit()
    return index


def prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode()).hexdigest()


def validate_structured_output(output: dict[str, object]) -> bool:
    return isinstance(output.get("label"), str) and isinstance(
        output.get("score"),
        int | float,
    )


def rebuild_custom_index(
    session: Session,
    tenant_id: str,
    asset_id: str,
    index_id: str,
    label: str,
) -> list[TemporalRecord]:
    asset = MediaAssetRepository(session, tenant_id).get(asset_id)
    if asset is None:
        raise ValueError("asset not found")
    frames = representative_frames(
        asset_id,
        extract_shots(session, tenant_id, asset_id),
    )
    records = TemporalRecordRepository(session, tenant_id)
    created = [
        records.add(
            TemporalRecord(
                asset_id=asset_id,
                index_id=index_id,
                start_ms=frame.timestamp_ms,
                end_ms=frame.timestamp_ms,
                payload={
                    "label": label,
                    "score": 1.0,
                    "source_frame_uri": frame.uri,
                },
            )
        )
        for frame in frames
    ]
    session.commit()
    return created


def promote_alias(index: Index, alias: str = "production") -> Index:
    index.metadata_ = {**index.metadata_, "alias": alias}
    return index


def evaluate_index(
    session: Session,
    tenant_id: str,
    index_id: str,
) -> EvaluationResult:
    records = TemporalRecordRepository(session, tenant_id).list_for_index(index_id)
    return EvaluationResult(
        index_id=index_id,
        record_count=len(records),
        passed=bool(records),
    )


def scoreboard_change_output(score_before: str, score_after: str) -> dict[str, object]:
    return {
        "label": "scoreboard_change",
        "score": 1.0 if score_before != score_after else 0.0,
    }


def replay_detection_output(has_replay_marker: bool) -> dict[str, object]:
    return {"label": "replay", "score": 1.0 if has_replay_marker else 0.0}


def speaker_tracking_output(speaker: str) -> dict[str, object]:
    return {"label": f"speaker:{speaker}", "score": 1.0}


def news_topic_boundary_output(topic_changed: bool) -> dict[str, object]:
    return {"label": "news_topic_boundary", "score": 1.0 if topic_changed else 0.0}
