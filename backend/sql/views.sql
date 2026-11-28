-- Views used by the API and the showcase queries.
-- Apply with:  python -m backend.setup_views
-- Safe to re-run (CREATE OR REPLACE).

-- Numbers each security's trading days 1, 2, 3, ... so we can step
-- "one trading day back" or "N trading days forward" without worrying
-- about weekends and market holidays.
CREATE OR REPLACE VIEW price_index AS
SELECT security_id,
       trade_date,
       adjusted_close,
       -- ROW_NUMBER() is BIGINT UNSIGNED; cast so "day_idx - 10" can go below zero safely.
       CAST(ROW_NUMBER() OVER (PARTITION BY security_id ORDER BY trade_date) AS SIGNED) AS day_idx
FROM prices;

-- One row per event with the stock's move and the XBI benchmark's move.
--   1-day window: close on the trading day before the event -> close on the event's trading day
--   5-day window: close on the trading day before the event -> close 4 trading days after it
-- Abnormal return = stock return minus XBI return (a simple market-adjusted model).
CREATE OR REPLACE VIEW event_returns AS
SELECT e.event_id,
       e.company_id,
       s.security_id,
       e.event_type,
       e.outcome,
       e.trading_day,
       base.adjusted_close                                   AS close_before,
       d1.adjusted_close                                     AS close_event_day,
       d1.adjusted_close / base.adjusted_close - 1           AS stock_return_1d,
       xd1.adjusted_close / xbase.adjusted_close - 1         AS xbi_return_1d,
       (d1.adjusted_close / base.adjusted_close - 1)
         - (xd1.adjusted_close / xbase.adjusted_close - 1)   AS abnormal_return_1d,
       d5.adjusted_close / base.adjusted_close - 1           AS stock_return_5d,
       xd5.adjusted_close / xbase.adjusted_close - 1         AS xbi_return_5d,
       (d5.adjusted_close / base.adjusted_close - 1)
         - (xd5.adjusted_close / xbase.adjusted_close - 1)   AS abnormal_return_5d
FROM events e
JOIN securities s       ON s.company_id = e.company_id
JOIN price_index d1     ON d1.security_id = s.security_id AND d1.trade_date = e.trading_day
JOIN price_index base   ON base.security_id = s.security_id AND base.day_idx = d1.day_idx - 1
LEFT JOIN price_index d5 ON d5.security_id = s.security_id AND d5.day_idx = d1.day_idx + 4
JOIN securities x       ON x.ticker = 'XBI'
JOIN price_index xd1    ON xd1.security_id = x.security_id AND xd1.trade_date = e.trading_day
JOIN price_index xbase  ON xbase.security_id = x.security_id AND xbase.day_idx = xd1.day_idx - 1
LEFT JOIN price_index xd5 ON xd5.security_id = x.security_id AND xd5.day_idx = xd1.day_idx + 4;
