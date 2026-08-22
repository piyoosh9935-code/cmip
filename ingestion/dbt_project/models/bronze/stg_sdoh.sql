select
    member_id,
    housing_status,
    food_security,
    transportation_access,
    income_bracket,
    batch_id::int as batch_id,
    loaded_at::timestamptz as loaded_at
from {{ source('bronze', 'sdoh') }}
