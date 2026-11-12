with with_prev as (
    select
        ticker,
        trade_date,
        close,
        lag(close) over (partition by ticker order by trade_date) as prev_close
    from {{ ref('fact_daily_prices') }}
)
select
    ticker,
    trade_date,
    close,
    prev_close,
    -- first day per ticker has no previous close, so the return stays NULL
    case when prev_close > 0 then round(close / prev_close - 1, 6) end as daily_return
from with_prev

