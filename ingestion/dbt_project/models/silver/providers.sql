{{ config(unique_key='provider_id') }}

select *
from {{ ref('stg_providers') }}
where provider_id is not null

{% if is_incremental() %}
and loaded_at > (select coalesce(max(loaded_at), '1900-01-01'::timestamptz) from {{ this }})
{% endif %}
