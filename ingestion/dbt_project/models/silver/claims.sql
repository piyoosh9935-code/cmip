{{ config(unique_key='claim_id') }}

select *
from {{ ref('stg_claims') }}
where claim_id is not null
  and member_id is not null
  and service_date is not null

{% if is_incremental() %}
and loaded_at > (select coalesce(max(loaded_at), '1900-01-01'::timestamptz) from {{ this }})
{% endif %}
