from datetime import datetime, timedelta, timezone

from . import config
from .clinical_reference import COHORTS
from .common import member_id, now_iso, rng_for

_ENCOUNTER_TYPES = ["office visit", "telehealth", "emergency department", "inpatient"]
_CONDITION_STATUSES = ["active", "resolved"]
_MEDICATION_STATUSES = ["active", "discontinued"]


def _volume(rng, cohorts, per_cohort_range, baseline_range, scale):
    base = sum(rng.randint(*per_cohort_range) for _ in cohorts) if cohorts else rng.randint(*baseline_range)
    return max(0, round(base * scale))


def _date(rng, batch_id, past_choices):
    offset = rng.choice(past_choices) if batch_id == 1 else rng.randint(-30, 0)
    return (datetime.now(timezone.utc) + timedelta(days=offset)).date().isoformat()


def generate_encounters_for_member(idx, cohorts, provider_ids, batch_id, scale) -> list[dict]:
    rng = rng_for("encounters", idx, batch_id)
    n = _volume(rng, cohorts, config.ENCOUNTERS_PER_MEMBER_PER_COHORT, config.BASELINE_ENCOUNTERS, scale)
    mid = member_id(idx)
    rows = []
    for i in range(n):
        etype = rng.choices(_ENCOUNTER_TYPES, weights=[70, 15, 10, 5])[0]
        rows.append(
            {
                "encounter_id": f"E-{mid}-{batch_id}-{i:04d}",
                "member_id": mid,
                "provider_id": rng.choice(provider_ids),
                "encounter_type": etype,
                "encounter_date": _date(rng, batch_id, [-750, -500, -300, -150, -60, -20]),
                "reason": rng.choice(cohorts) if cohorts else "routine care",
                "batch_id": batch_id,
                "loaded_at": now_iso(),
            }
        )
    return rows


def generate_conditions_for_member(idx, cohorts, batch_id, scale) -> list[dict]:
    rng = rng_for("conditions", idx, batch_id)
    n = _volume(rng, cohorts, config.CONDITIONS_PER_MEMBER_PER_COHORT, (0, 1), scale)
    mid = member_id(idx)
    rows = []
    for i in range(n):
        cohort = rng.choice(cohorts) if cohorts else None
        if not cohort:
            continue
        code, desc = rng.choice(COHORTS[cohort]["conditions"])
        rows.append(
            {
                "condition_id": f"CD-{mid}-{batch_id}-{i:04d}",
                "member_id": mid,
                "icd10_code": code,
                "icd10_desc": desc,
                "onset_date": _date(rng, batch_id, [-1500, -1000, -600, -300]),
                "status": rng.choices(_CONDITION_STATUSES, weights=[85, 15])[0],
                "batch_id": batch_id,
                "loaded_at": now_iso(),
            }
        )
    return rows


def generate_medications_for_member(idx, cohorts, batch_id, scale) -> list[dict]:
    rng = rng_for("medications", idx, batch_id)
    n = _volume(rng, cohorts, config.MEDICATIONS_PER_MEMBER_PER_COHORT, (0, 1), scale)
    mid = member_id(idx)
    rows = []
    for i in range(n):
        cohort = rng.choice(cohorts) if cohorts else None
        if not cohort:
            continue
        med = rng.choice(COHORTS[cohort]["medications"])
        status = rng.choices(_MEDICATION_STATUSES, weights=[80, 20])[0]
        start = _date(rng, batch_id, [-900, -600, -300, -120, -30])
        rows.append(
            {
                "medication_id": f"MD-{mid}-{batch_id}-{i:04d}",
                "member_id": mid,
                "medication_name": med,
                "start_date": start,
                "end_date": _date(rng, batch_id, [-60, -30, -10]) if status == "discontinued" else None,
                "status": status,
                "batch_id": batch_id,
                "loaded_at": now_iso(),
            }
        )
    return rows
