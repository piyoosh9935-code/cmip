select
    condition_id,
    member_id,
    icd10_code,
    icd10_desc,
    onset_date::date as onset_date,
    status,
    batch_id::int as batch_id,
    loaded_at::timestamptz as loaded_at
from {{ source('bronze', 'ehr_conditions') }}
