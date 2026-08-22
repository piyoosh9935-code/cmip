from ingestion.synthetic_data_gen import config
from ingestion.synthetic_data_gen.claims import generate_claims_for_member
from ingestion.synthetic_data_gen.clinical_reference import COHORTS
from ingestion.synthetic_data_gen.members import (
    cohorts_for_member,
    member_index_range_for_batch,
    total_members_through_batch,
)


def test_cohort_assignment_is_deterministic():
    assert cohorts_for_member(17) == cohorts_for_member(17)
    assert cohorts_for_member(17) == cohorts_for_member(17)  # stable across batches too


def test_cohort_assignment_only_uses_known_cohorts():
    for idx in range(0, config.N_MEMBERS_INITIAL, 7):
        for cohort in cohorts_for_member(idx):
            assert cohort in COHORTS


def test_batch_member_ranges_do_not_overlap():
    batch1 = set(member_index_range_for_batch(1))
    batch2 = set(member_index_range_for_batch(2))
    batch3 = set(member_index_range_for_batch(3))
    assert not batch1 & batch2
    assert not batch2 & batch3
    assert len(batch1) == config.N_MEMBERS_INITIAL
    assert len(batch2) == config.N_NEW_MEMBERS_PER_BATCH


def test_total_members_through_batch_matches_ranges():
    assert total_members_through_batch(1) == config.N_MEMBERS_INITIAL
    assert total_members_through_batch(2) == config.N_MEMBERS_INITIAL + config.N_NEW_MEMBERS_PER_BATCH
    assert max(member_index_range_for_batch(2)) + 1 == total_members_through_batch(2)


def test_claims_reference_only_valid_providers():
    providers = [f"P-{i:04d}" for i in range(40)]
    cohorts = cohorts_for_member(3)
    rows = generate_claims_for_member(3, cohorts, providers, batch_id=1, scale=1.0)
    assert rows
    for row in rows:
        assert row["provider_id"] in providers
        assert row["member_id"] == "M-00003"
        assert row["paid_amount"] > 0


def test_incremental_scale_reduces_volume():
    cohorts = ["diabetes", "hypertension"]
    providers = [f"P-{i:04d}" for i in range(40)]
    full = generate_claims_for_member(50, cohorts, providers, batch_id=1, scale=1.0)
    incremental = generate_claims_for_member(50, cohorts, providers, batch_id=2, scale=config.INCREMENTAL_ACTIVITY_FRACTION)
    assert len(incremental) < len(full)
