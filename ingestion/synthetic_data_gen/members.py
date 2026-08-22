from faker import Faker

from . import config
from .clinical_reference import COHORTS, PROVIDER_SPECIALTIES
from .common import member_id, now_iso, provider_id, rng_for

_COHORT_NAMES = list(COHORTS.keys())
_TOTAL_COHORT_SLOTS = sum(config.COHORTS.values())
_PLAN_TYPES = ["HMO", "PPO", "Medicare Advantage", "Medicaid MCO"]
_REGIONS = ["Northeast", "Midwest", "South", "West"]


def member_index_range_for_batch(batch_id: int) -> range:
    if batch_id == 1:
        return range(0, config.N_MEMBERS_INITIAL)
    start = config.N_MEMBERS_INITIAL + (batch_id - 2) * config.N_NEW_MEMBERS_PER_BATCH
    return range(start, start + config.N_NEW_MEMBERS_PER_BATCH)


def total_members_through_batch(batch_id: int) -> int:
    if batch_id <= 1:
        return config.N_MEMBERS_INITIAL
    return config.N_MEMBERS_INITIAL + (batch_id - 1) * config.N_NEW_MEMBERS_PER_BATCH


def cohorts_for_member(index: int) -> list[str]:
    """Deterministic given only the member index + global seed - so the same member
    always has the same cohorts regardless of which batch generated their activity."""
    rng = rng_for("cohorts", index)
    roll = rng.random() * _TOTAL_COHORT_SLOTS
    cumulative = 0
    primary = None
    for name, weight in config.COHORTS.items():
        cumulative += weight
        if roll < cumulative:
            primary = name
            break
    if primary is None:
        return []

    cohorts = [primary]
    # ~15% chance of a plausible comorbidity
    comorbid_pairs = {
        "diabetes": ["hypertension", "chf"],
        "chf": ["hypertension", "copd"],
        "copd": ["hypertension"],
        "hypertension": ["diabetes"],
        "depression": ["diabetes", "hypertension"],
    }
    if rng.random() < 0.15:
        candidates = comorbid_pairs.get(primary, [])
        if candidates:
            cohorts.append(rng.choice(candidates))
    return cohorts


def generate_members_batch(batch_id: int) -> list[dict]:
    fake = Faker()
    Faker.seed(config.SEED * 1000 + batch_id)
    rows = []
    for idx in member_index_range_for_batch(batch_id):
        rng = rng_for("member_row", idx)
        gender = rng.choice(["F", "M"])
        dob = fake.date_of_birth(minimum_age=19, maximum_age=89)
        rows.append(
            {
                "member_id": member_id(idx),
                "first_name": fake.first_name_female() if gender == "F" else fake.first_name_male(),
                "last_name": fake.last_name(),
                "date_of_birth": dob.isoformat(),
                "gender": gender,
                "plan_type": rng.choice(_PLAN_TYPES),
                "region": rng.choice(_REGIONS),
                "enrollment_start": fake.date_between(start_date="-6y", end_date="-3M").isoformat(),
                "cohorts": ",".join(cohorts_for_member(idx)),
                "batch_id": batch_id,
                "loaded_at": now_iso(),
            }
        )
    return rows


def generate_providers() -> list[dict]:
    """Static provider directory, generated once (batch 1 only)."""
    fake = Faker()
    Faker.seed(config.SEED)
    rows = []
    for idx in range(40):
        rng = rng_for("provider_row", idx)
        rows.append(
            {
                "provider_id": provider_id(idx),
                "provider_name": f"Dr. {fake.first_name()} {fake.last_name()}",
                "specialty": rng.choice(PROVIDER_SPECIALTIES),
                "npi": f"{1_000_000_000 + idx}",
                "region": rng.choice(_REGIONS),
                "batch_id": 1,
                "loaded_at": now_iso(),
            }
        )
    return rows


def provider_ids() -> list[str]:
    return [provider_id(i) for i in range(40)]
