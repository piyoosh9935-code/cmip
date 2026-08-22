select
    member_id,
    first_name,
    last_name,
    date_of_birth::date as date_of_birth,
    gender,
    plan_type,
    region,
    enrollment_start::date as enrollment_start,
    nullif(cohorts, '') as cohorts,
    batch_id::int as batch_id,
    loaded_at::timestamptz as loaded_at
from {{ source('bronze', 'members') }}
