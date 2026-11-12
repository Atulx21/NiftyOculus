-- Averages are only reported once a full window of trading days exists.
select
    ticker,
    trade_date,
    close,
    case when count(*) over w20 = 20 then round(avg(close) over w20, 4) end as ma_20,
    case when count(*) over w50 = 50 then round(avg(close) over w50, 4) end as ma_50
from {{ ref('fact_daily_prices') }}
window
    w20 as (partition by ticker order by trade_date rows between 19 preceding and current row),
    w50 as (partition by ticker order by trade_date rows between 49 preceding and current row)

