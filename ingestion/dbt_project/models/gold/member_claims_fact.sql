select
    cl.claim_id,
    cl.member_id,
    cl.claim_type,
    cl.diagnosis_code,
    cl.diagnosis_desc,
    cl.procedure_code,
    cl.procedure_desc,
    cl.service_date,
    cl.paid_amount,
    p.provider_id,
    p.provider_name,
    p.specialty as provider_specialty
from {{ ref('claims') }} cl
left join {{ ref('providers') }} p on p.provider_id = cl.provider_id
