select
    claim_id,
    member_id,
    provider_id,
    claim_type,
    diagnosis_code,
    diagnosis_desc,
    procedure_code,
    procedure_desc,
    service_date::date as service_date,
    paid_amount::numeric(10, 2) as paid_amount,
    batch_id::int as batch_id,
    loaded_at::timestamptz as loaded_at
from {{ source('bronze', 'claims') }}
