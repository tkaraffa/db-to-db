select
    *
from
    {{ source('raw', 'test_table') }}

{% if is_incremental %}
    where date >= '{{ var("start_date") }}'
    and date < '{{ var("end_date") }}'
{% endif %}
