import hashlib
from time import perf_counter

from sqlalchemy.orm import Session

from apps.clips import create_virtual_clip
from apps.persistence.models import Alert, Event, EventRule, TemporalRecord, VirtualClip
from apps.persistence.repositories import (
    AlertRepository,
    EventRepository,
    EventRuleRepository,
    TemporalRecordRepository,
)


def store_event_rule(
    session: Session,
    tenant_id: str,
    name: str,
    query: str,
    target_url: str | None = None,
) -> EventRule:
    rule = EventRuleRepository(session, tenant_id).add(
        EventRule(name=name, query=query, target_url=target_url)
    )
    session.commit()
    return rule


def evaluate_event_rule(
    session: Session,
    tenant_id: str,
    rule: EventRule,
) -> list[Event]:
    events: list[Event] = []
    for record in TemporalRecordRepository(session, tenant_id).list():
        evidence = str(record.payload.get("text", record.payload.get("label", "")))
        if rule.query.lower() not in evidence.lower():
            continue
        event_id = stable_event_id(rule.id, record)
        existing = EventRepository(session, tenant_id).get(event_id)
        if existing is not None:
            events.append(existing)
            continue
        event = EventRepository(session, tenant_id).add(
            Event(
                id=event_id,
                stream_id=str(record.payload.get("stream_id"))
                if record.payload.get("stream_id") is not None
                else None,
                asset_id=record.asset_id,
                rule_name=rule.name,
                start_ms=record.start_ms,
                end_ms=record.end_ms,
                payload={"evidence": evidence},
            )
        )
        events.append(event)
    session.commit()
    return events


def stable_event_id(rule_id: str, record: TemporalRecord) -> str:
    key = f"{rule_id}:{record.asset_id}:{record.start_ms}:{record.end_ms}"
    return hashlib.sha256(key.encode()).hexdigest()[:32]


def websocket_event_payload(event: Event) -> dict[str, object]:
    return {
        "event_id": event.id,
        "rule_name": event.rule_name,
        "start_ms": event.start_ms,
        "end_ms": event.end_ms,
        "payload": event.payload,
    }


def deliver_webhook_alert(
    session: Session,
    tenant_id: str,
    event_id: str,
    target_url: str,
    fail_once: bool = False,
) -> Alert:
    alert = AlertRepository(session, tenant_id).add(
        Alert(event_id=event_id, target_url=target_url, status="pending")
    )
    _attempt_delivery(alert, fail_once)
    if alert.status != "delivered":
        _attempt_delivery(alert, False)
    session.commit()
    return alert


def create_event_clip(
    session: Session,
    tenant_id: str,
    event: Event,
) -> VirtualClip:
    if event.asset_id is None:
        raise ValueError("event has no asset")
    return create_virtual_clip(
        session,
        tenant_id,
        f"event-{event.id}",
        [
            {
                "asset_id": event.asset_id,
                "start_ms": event.start_ms,
                "end_ms": event.end_ms,
            }
        ],
    )


def measure_event_latency(
    session: Session,
    tenant_id: str,
    rule: EventRule,
) -> float:
    started_at = perf_counter()
    evaluate_event_rule(session, tenant_id, rule)
    return perf_counter() - started_at


def _attempt_delivery(alert: Alert, fail: bool) -> None:
    alert.attempts += 1
    alert.status = "failed" if fail else "delivered"
