-- Top 5 gainers and top 5 losers for every trading day.
with ranked as (
    select
        r.trade_date,
        r.ticker,
        s.company,
        s.sector,
        r.close,
        r.daily_return,
        row_number() over (partition by r.trade_date order by r.daily_return desc) as gainer_rank,
        row_number() over (partition by r.trade_date order by r.daily_return asc)  as loser_rank
    from {{ ref('daily_returns') }} r
    join {{ ref('dim_stock') }} s on s.ticker = r.ticker
    where r.daily_return is not null
)
select trade_date, ticker, company, sector, close, daily_return,
       'gainer' as rank_type, gainer_rank as rank
from ranked where gainer_rank <= 5
union all
select trade_date, ticker, company, sector, close, daily_return,
       'loser' as rank_type, loser_rank as rank
from ranked where loser_rank <= 5

