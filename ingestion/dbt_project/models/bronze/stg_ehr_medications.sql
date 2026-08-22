select
    medication_id,
    member_id,
    medication_name,
    start_date::date as start_date,
    end_date::date as end_date,
    status,
    batch_id::int as batch_id,
    loaded_at::timestamptz as loaded_at
from {{ source('bronze', 'ehr_medications') }}
