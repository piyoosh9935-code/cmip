"""Seeded synthetic data generator for CMIP.

Run `python -m ingestion.synthetic_data_gen.generate --batch 1` for the initial full
population, then `--batch 2`, `--batch 3`, ... to simulate new data arriving over time
(new members enrolling + existing members generating new claims/encounters/notes).
Each batch writes its own `<table>_batch<N>.csv` containing only the NEW rows for that
batch - the Postgres loader appends these into bronze, and dbt's silver models pick up
only what's new via `is_incremental()`.
"""

import argparse
import os

import pandas as pd

from . import config
from .claims import generate_claims_for_member
from .ehr import (
    generate_conditions_for_member,
    generate_encounters_for_member,
    generate_medications_for_member,
)
from .members import (
    cohorts_for_member,
    generate_members_batch,
    generate_providers,
    member_index_range_for_batch,
    provider_ids,
    total_members_through_batch,
)
from .notes import generate_notes_for_member
from .sdoh import generate_sdoh_for_member


def _write(rows: list[dict], name: str, batch_id: int) -> int:
    if not rows:
        print(f"  {name}: 0 rows (skipped)")
        return 0
    os.makedirs(config.RAW_DIR, exist_ok=True)
    path = os.path.join(config.RAW_DIR, f"{name}_batch{batch_id}.csv")
    pd.DataFrame(rows).to_csv(path, index=False)
    print(f"  {name}: {len(rows):>5} rows -> {os.path.relpath(path)}")
    return len(rows)


def run(batch_id: int) -> None:
    print(f"Generating batch {batch_id} (seed={config.SEED})")
    new_idxs = list(member_index_range_for_batch(batch_id))
    existing_idxs = list(range(0, total_members_through_batch(batch_id - 1))) if batch_id > 1 else []
    providers = provider_ids()

    _write(generate_members_batch(batch_id), "members", batch_id)
    if batch_id == 1:
        _write(generate_providers(), "providers", batch_id)

    buckets: dict[str, list[dict]] = {
        "claims": [], "ehr_encounters": [], "ehr_conditions": [],
        "ehr_medications": [], "clinical_notes": [], "sdoh": [],
    }

    for idx in new_idxs:
        cohorts = cohorts_for_member(idx)
        buckets["claims"] += generate_claims_for_member(idx, cohorts, providers, batch_id, scale=1.0)
        buckets["ehr_encounters"] += generate_encounters_for_member(idx, cohorts, providers, batch_id, scale=1.0)
        buckets["ehr_conditions"] += generate_conditions_for_member(idx, cohorts, batch_id, scale=1.0)
        buckets["ehr_medications"] += generate_medications_for_member(idx, cohorts, batch_id, scale=1.0)
        buckets["clinical_notes"] += generate_notes_for_member(idx, cohorts, providers, batch_id, scale=1.0)
        buckets["sdoh"].append(generate_sdoh_for_member(idx, batch_id))

    for idx in existing_idxs:
        cohorts = cohorts_for_member(idx)
        scale = config.INCREMENTAL_ACTIVITY_FRACTION
        buckets["claims"] += generate_claims_for_member(idx, cohorts, providers, batch_id, scale)
        buckets["ehr_encounters"] += generate_encounters_for_member(idx, cohorts, providers, batch_id, scale)
        buckets["ehr_conditions"] += generate_conditions_for_member(idx, cohorts, batch_id, scale)
        buckets["ehr_medications"] += generate_medications_for_member(idx, cohorts, batch_id, scale)
        buckets["clinical_notes"] += generate_notes_for_member(idx, cohorts, providers, batch_id, scale)
        # sdoh is a one-time dimension per member, not regenerated for existing members

    for name, rows in buckets.items():
        _write(rows, name, batch_id)

    print(
        f"Batch {batch_id} done: {len(new_idxs)} new members, "
        f"{len(existing_idxs)} existing members with new activity"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", type=int, default=1, help="batch number, starting at 1")
    args = parser.parse_args()
    run(args.batch)
