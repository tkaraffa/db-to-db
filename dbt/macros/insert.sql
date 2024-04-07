{% macro insert(source_table, target_table, where_clauses=[]) %}

insert into {{ target_table }}
select * from {{ source_table }}

{% if where_clauses %}
where
    {% for clause in where_clauses %}
    {{ clause }}
    {% if not loop.last %}
    and
    {% endif %}
    {% endfor %}
{% endif %}

{% endmacro %}