from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.persistence.models import MediaAsset, TemporalRecord


@dataclass
class TenantQuota:
    max_assets: int

    def allows_asset_count(self, asset_count: int) -> bool:
        return asset_count < self.max_assets


@dataclass
class RateLimiter:
    max_requests: int
    counts: dict[str, int] = field(default_factory=dict)

    def allow(self, tenant_id: str) -> bool:
        current = self.counts.get(tenant_id, 0)
        if current >= self.max_requests:
            return False
        self.counts[tenant_id] = current + 1
        return True


def metrics_snapshot(session: Session, tenant_id: str) -> dict[str, int]:
    asset_count = len(
        list(
            session.scalars(
                select(MediaAsset).where(MediaAsset.tenant_id == tenant_id)
            )
        )
    )
    temporal_record_count = len(
        list(
            session.scalars(
                select(TemporalRecord).where(TemporalRecord.tenant_id == tenant_id)
            )
        )
    )
    return {
        "assets": asset_count,
        "temporal_records": temporal_record_count,
    }
