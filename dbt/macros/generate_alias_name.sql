{# 
    Inspired by:
    https://medium.com/data-manypets/how-to-customise-dbts-model-naming-for-easy-developing-on-production-1238559a939a 
#}

{% macro generate_alias_name(custom_alias_name=none, node=none) -%}
    {%- if custom_alias_name is none -%}
        {%- set table_name = node.name -%}
    {%- else -%}
        {%- set table_name = custom_alias_name | trim -%}
    {%- endif -%}

    {%- if target.name.startswith('local_dev') -%}
        {#- Get the custom schema name -#}
        {%- set schema_prefix = node.unrendered_config.schema | trim %}

        {#- Highlight if schema hasn't been assigned right -#}
        {%- if not schema_prefix -%}
            {%- set schema_prefix = 'NO_ASSIGNED_SCHEMA' %}
        {%- endif -%}

        {{ schema_prefix ~ "__" ~ table_name }}

    {%- else -%}
        {{ table_name }}
    {%- endif -%}
{%- endmacro %}
