-- Volatility = standard deviation of the last 20 daily returns.
select
    ticker,
    trade_date,
    daily_return,
    case when count(daily_return) over w = 20
         then round(stddev_samp(daily_return) over w, 6) end as volatility_20d
from {{ ref('daily_returns') }}
window w as (partition by ticker order by trade_date rows between 19 preceding and current row)

