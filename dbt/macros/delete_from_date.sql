{% macro delete_from_date() %}

{% if is_incremental() %}


{% set start = cast('{{ var("start_date") }}' as date) %}
{% set end = cast('{{ var("end_date") }}' as date) %}

delete from {{ this }}
where date in (
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date=start,
        end_date=end
    ) }}
)
{% endif %}

{% endmacro %}