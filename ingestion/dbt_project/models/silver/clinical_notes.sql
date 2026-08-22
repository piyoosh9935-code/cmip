{{ config(unique_key='note_id') }}

select *
from {{ ref('stg_clinical_notes') }}
where note_id is not null
  and member_id is not null
  and note_text is not null

{% if is_incremental() %}
and loaded_at > (select coalesce(max(loaded_at), '1900-01-01'::timestamptz) from {{ this }})
{% endif %}
