from datetime import datetime, timedelta, timezone

from . import config
from .clinical_reference import COHORTS
from .common import member_id, now_iso, rng_for

_CLAIM_TYPES = ["professional", "institutional", "pharmacy"]


def _volume(rng, cohorts: list[str], per_cohort_range, baseline_range, scale: float) -> int:
    if not cohorts:
        base = rng.randint(*baseline_range)
    else:
        base = sum(rng.randint(*per_cohort_range) for _ in cohorts)
    return max(0, round(base * scale))


def generate_claims_for_member(
    idx: int, cohorts: list[str], provider_ids: list[str], batch_id: int, scale: float
) -> list[dict]:
    rng = rng_for("claims", idx, batch_id)
    n = _volume(rng, cohorts, config.CLAIMS_PER_MEMBER_PER_COHORT, config.BASELINE_CLAIMS, scale)
    mid = member_id(idx)
    rows = []
    for i in range(n):
        cohort = rng.choice(cohorts) if cohorts else None
        if cohort:
            dx_code, dx_desc = rng.choice(COHORTS[cohort]["conditions"])
            px_code, px_desc = rng.choice(COHORTS[cohort]["procedures"])
        else:
            dx_code, dx_desc = "Z00.00", "General adult medical examination"
            px_code, px_desc = "99396", "Periodic comprehensive preventive exam"
        offset_days = (
            rng.choice([-800, -600, -400, -200, -90, -45, -10]) if batch_id == 1
            else rng.randint(-30, 0)
        )
        service_date = (datetime.now(timezone.utc) + timedelta(days=offset_days)).date().isoformat()
        rows.append(
            {
                "claim_id": f"C-{mid}-{batch_id}-{i:04d}",
                "member_id": mid,
                "provider_id": rng.choice(provider_ids),
                "claim_type": rng.choice(_CLAIM_TYPES),
                "diagnosis_code": dx_code,
                "diagnosis_desc": dx_desc,
                "procedure_code": px_code,
                "procedure_desc": px_desc,
                "service_date": service_date,
                "paid_amount": round(rng.uniform(25, 4500), 2),
                "batch_id": batch_id,
                "loaded_at": now_iso(),
            }
        )
    return rows
