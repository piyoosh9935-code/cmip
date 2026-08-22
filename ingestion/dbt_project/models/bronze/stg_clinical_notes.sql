select
    note_id,
    member_id,
    provider_id,
    note_type,
    note_date::date as note_date,
    note_text,
    cohort_tag,
    batch_id::int as batch_id,
    loaded_at::timestamptz as loaded_at
from {{ source('bronze', 'clinical_notes') }}
