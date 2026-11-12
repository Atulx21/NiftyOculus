select
    ticker,
    replace(ticker, '.NS', '') as symbol,
    company,
    sector
from {{ ref('tickers') }}

