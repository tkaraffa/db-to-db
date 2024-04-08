
{% macro delete_from(ref, gte_column=None, gte_value=None, lt_column=None, lt_value=None) %}
delete from {{ ref }}

    {% if gte_column %}
    {% set gte_clause = gte_column ~ " >= '" ~ gte_value ~ "'" %}
    {% else %}
    {% set gte_clause = None %}
    {% endif %}

    {% if lt_column %}
    {% set lt_clause = lt_column ~ " < '" ~ lt_value ~ "'" %}
    {% else %}
    {% set lt_clause = None %}
    {% endif %}

    {% for clause in [gte_clause, lt_clause] if clause %}
    {% if loop.first %}
    where {{ clause }}
    {% else %}
    and {{ clause }}
    {% endif %}
    {% endfor %}

{% endmacro %}
