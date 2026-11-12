-- One row per calendar day between the first and last trading date.
with bounds as (
    select min(trade_date) as first_day, max(trade_date) as last_day
    from {{ source('silver', 'daily_prices') }}
)
select
    d::date                                     as date_day,
    extract(year from d)::int                   as year,
    extract(quarter from d)::int                as quarter,
    extract(month from d)::int                  as month,
    extract(isodow from d)::int                 as day_of_week,  -- 1 = Monday
    extract(isodow from d) >= 6                 as is_weekend
from bounds,
     generate_series(first_day, last_day, interval '1 day') as d

