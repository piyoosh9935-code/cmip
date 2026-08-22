select
    medication_id,
    member_id,
    medication_name,
    start_date,
    end_date,
    status
from {{ ref('ehr_medications') }}
where status = 'active'
