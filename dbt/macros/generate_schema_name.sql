{# Use the schema name exactly as configured (gold / silver) instead of dbt's default
   "<target schema>_<custom schema>" so tables land in the schemas we designed. #}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {{ custom_schema_name | trim if custom_schema_name else target.schema }}
{%- endmacro %}

