select
    encounter_id,
    member_id,
    provider_id,
    encounter_type,
    encounter_date::date as encounter_date,
    reason,
    batch_id::int as batch_id,
    loaded_at::timestamptz as loaded_at
from {{ source('bronze', 'ehr_encounters') }}
