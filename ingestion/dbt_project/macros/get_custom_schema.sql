{# Override dbt's default "<target_schema>_<custom_schema>" naming so models with
   +schema: bronze/silver/gold land in exactly that schema, matching the schemas the
   Python loader and init_extensions.sql already created. #}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
