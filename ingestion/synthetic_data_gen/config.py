import os

SEED = 42

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "bronze_silver_gold", "raw")

N_MEMBERS_INITIAL = 400
N_NEW_MEMBERS_PER_BATCH = 15

# cohort name -> (target member count in initial batch, weight for incremental batches)
COHORTS = {
    "diabetes": 120,
    "hypertension": 200,
    "chf": 60,
    "copd": 50,
    "depression": 40,
}

# average number of claims/encounters/notes generated per member per batch, scaled by
# how many cohorts they belong to (sicker members generate more records - matches how
# real utilization data looks, and gives retrieval something real to differentiate on)
CLAIMS_PER_MEMBER_PER_COHORT = (8, 20)
ENCOUNTERS_PER_MEMBER_PER_COHORT = (3, 8)
CONDITIONS_PER_MEMBER_PER_COHORT = (1, 3)
MEDICATIONS_PER_MEMBER_PER_COHORT = (1, 4)
NOTES_PER_MEMBER_PER_COHORT = (2, 5)

# members with zero cohorts still get a small baseline of routine-care activity
BASELINE_CLAIMS = (0, 4)
BASELINE_ENCOUNTERS = (0, 2)
BASELINE_NOTES = (0, 1)

# incremental batches (batch_id >= 2) generate this fraction of the initial volume of
# new activity for existing members, plus full volume for any new members
INCREMENTAL_ACTIVITY_FRACTION = 0.08
