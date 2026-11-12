select
    r.trade_date,
    s.sector,
    count(*)                       as stocks,
    round(avg(r.daily_return), 6)  as avg_return,
    sum(f.volume)                  as total_volume
from {{ ref('daily_returns') }} r
join {{ ref('dim_stock') }} s on s.ticker = r.ticker
join {{ ref('fact_daily_prices') }} f on f.ticker = r.ticker and f.trade_date = r.trade_date
where r.daily_return is not null
group by r.trade_date, s.sector

