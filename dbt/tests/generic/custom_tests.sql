{# Custom data-quality tests. A dbt test is a query that returns the BAD rows;
   the test passes when it returns zero rows. #}

{# Prices must be sane: high >= low and close > 0. #}
{% test valid_ohlc(model) %}
select *
from {{ model }}
where high < low or close <= 0
{% endtest %}

{# Uniqueness of a column combination (e.g. ticker + trade_date). #}
{% test unique_combination(model, columns) %}
select {{ columns | join(', ') }}, count(*) as n
from {{ model }}
group by {{ columns | join(', ') }}
having count(*) > 1
{% endtest %}

