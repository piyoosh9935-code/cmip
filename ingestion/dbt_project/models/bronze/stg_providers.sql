select
    provider_id,
    provider_name,
    specialty,
    npi,
    region,
    batch_id::int as batch_id,
    loaded_at::timestamptz as loaded_at
from {{ source('bronze', 'providers') }}
