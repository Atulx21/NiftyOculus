{{ config(
    materialized='incremental',
    unique_key=['ticker', 'trade_date'],
    incremental_strategy='delete+insert'
) }}

select
    ticker, trade_date, open, high, low, close, adj_close, volume, ingestion_date
from {{ source('silver', 'daily_prices') }}

{% if is_incremental() %}
-- Only look at recent dates. The 7-day overlap picks up late corrections, and
-- delete+insert on (ticker, trade_date) replaces the overlap, so re-runs never duplicate.
where trade_date > (select max(trade_date) from {{ this }}) - 7
{% endif %}

