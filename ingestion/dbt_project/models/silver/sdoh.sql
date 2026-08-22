{{ config(unique_key='member_id') }}

select *
from {{ ref('stg_sdoh') }}
where member_id is not null

{% if is_incremental() %}
and loaded_at > (select coalesce(max(loaded_at), '1900-01-01'::timestamptz) from {{ this }})
{% endif %}
