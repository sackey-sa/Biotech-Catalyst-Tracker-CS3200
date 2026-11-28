-- Backend-only views used by the API.
-- Apply with:  python -m backend.setup_views
-- Safe to re-run (CREATE OR REPLACE).
--
-- The 1-day returns come from the team's event_returns view in
-- sql/02_calculations.sql (run that in Workbench first). Don't define
-- event_returns here: setup_views.py only allows price_index and event_windows.

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

-- One row per event with the 5-day move of the stock and of XBI.
--   Window: close on the trading day before the event -> close 4 trading days after it.
--   That's the same starting price as the team's daily_return, so 1-day and
--   5-day numbers line up.
-- Every event gets a row (LEFT JOINs): if a price is missing, the returns are NULL.
CREATE OR REPLACE VIEW event_windows AS
SELECT e.event_id,
       s.security_id,
       d5.adjusted_close / base.adjusted_close - 1           AS stock_return_5d,
       xd5.adjusted_close / xbase.adjusted_close - 1         AS xbi_return_5d,
       (d5.adjusted_close / base.adjusted_close - 1)
         - (xd5.adjusted_close / xbase.adjusted_close - 1)   AS abnormal_return_5d
FROM events e
LEFT JOIN securities s       ON s.company_id = e.company_id
LEFT JOIN price_index d1     ON d1.security_id = s.security_id AND d1.trade_date = e.trading_day
LEFT JOIN price_index base   ON base.security_id = s.security_id AND base.day_idx = d1.day_idx - 1
LEFT JOIN price_index d5     ON d5.security_id = s.security_id AND d5.day_idx = d1.day_idx + 4
LEFT JOIN securities x       ON x.ticker = 'XBI'
LEFT JOIN price_index xd1    ON xd1.security_id = x.security_id AND xd1.trade_date = e.trading_day
LEFT JOIN price_index xbase  ON xbase.security_id = x.security_id AND xbase.day_idx = xd1.day_idx - 1
LEFT JOIN price_index xd5    ON xd5.security_id = x.security_id AND xd5.day_idx = xd1.day_idx + 4;
