-- Source table for retrieval/qdrant/ingest.py and retrieval/bm25/build_index.py:
-- one row per clinical note, denormalized with provider context. Every retrieval call
-- downstream filters on member_id, so that column must always be present and non-null.
select
    n.note_id,
    n.member_id,
    n.note_type,
    n.note_date,
    n.note_text,
    n.cohort_tag,
    p.provider_id,
    p.provider_name,
    p.specialty as provider_specialty
from {{ ref('clinical_notes') }} n
left join {{ ref('providers') }} p on p.provider_id = n.provider_id
