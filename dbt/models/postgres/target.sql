{{ config(pre_hook="{{ delete_from_date() }}") }}

select
    *
from
    {{ source('mysql', 'source') }}

{% if is_incremental() %}


{% set start = cast('{{ var("start_date") }}' as date) %}
{% set end = cast('{{ var("end_date") }}' as date) %}

where date in (
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date=start,
        end_date=end
    ) }}
)
{% endif %}
