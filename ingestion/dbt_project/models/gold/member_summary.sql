with claim_agg as (
    select member_id, count(*) as total_claims, sum(paid_amount) as total_paid_amount,
           max(service_date) as last_claim_date
    from {{ ref('claims') }}
    group by member_id
),
encounter_agg as (
    select member_id, count(*) as total_encounters, max(encounter_date) as last_encounter_date
    from {{ ref('ehr_encounters') }}
    group by member_id
),
condition_agg as (
    select member_id, string_agg(distinct icd10_desc, '; ') as active_conditions
    from {{ ref('ehr_conditions') }}
    where status = 'active'
    group by member_id
),
medication_agg as (
    select member_id, count(*) filter (where status = 'active') as active_medication_count
    from {{ ref('ehr_medications') }}
    group by member_id
),
note_agg as (
    select member_id, count(*) as total_notes, max(note_date) as last_note_date
    from {{ ref('clinical_notes') }}
    group by member_id
)

select
    m.member_id,
    m.first_name,
    m.last_name,
    m.date_of_birth,
    date_part('year', age(m.date_of_birth))::int as age,
    m.gender,
    m.plan_type,
    m.region,
    m.enrollment_start,
    m.cohorts,
    s.housing_status,
    s.food_security,
    s.transportation_access,
    s.income_bracket,
    coalesce(c.total_claims, 0) as total_claims,
    coalesce(c.total_paid_amount, 0) as total_paid_amount,
    c.last_claim_date,
    coalesce(e.total_encounters, 0) as total_encounters,
    e.last_encounter_date,
    cond.active_conditions,
    coalesce(med.active_medication_count, 0) as active_medication_count,
    coalesce(n.total_notes, 0) as total_notes,
    n.last_note_date
from {{ ref('members') }} m
left join {{ ref('sdoh') }} s on s.member_id = m.member_id
left join claim_agg c on c.member_id = m.member_id
left join encounter_agg e on e.member_id = m.member_id
left join condition_agg cond on cond.member_id = m.member_id
left join medication_agg med on med.member_id = m.member_id
left join note_agg n on n.member_id = m.member_id
