-- =============================================================
-- 02_calculations.sql
-- How much each stock moved because of its own news.
-- Run after the tables exist. Safe to run again.
-- =============================================================

USE biotech_catalyst;

DROP PROCEDURE IF EXISTS compute_abnormal_returns;
DROP VIEW      IF EXISTS event_returns;
DROP FUNCTION  IF EXISTS daily_return;


-- -------------------------------------------------------------
-- 1. daily_return: how much one stock moved on one day
--
--    return = today's price / previous trading day's price - 1
--
--    "Previous trading day" = the closest earlier date with a price,
--    so a Monday compares to the Friday before it.
--    Returns NULL if a price is missing.
-- -------------------------------------------------------------
DELIMITER //

CREATE FUNCTION daily_return(stock_id INT, on_date DATE)
RETURNS DECIMAL(12,6)
READS SQL DATA
BEGIN
  DECLARE today_price    DECIMAL(12,4);
  DECLARE previous_price DECIMAL(12,4);

  -- Price on the day itself
  SET today_price = (
    SELECT adjusted_close
    FROM prices
    WHERE security_id = stock_id
      AND trade_date = on_date
  );

  -- Price on the most recent trading day before it
  SET previous_price = (
    SELECT adjusted_close
    FROM prices
    WHERE security_id = stock_id
      AND trade_date < on_date
    ORDER BY trade_date DESC
    LIMIT 1
  );

  IF today_price IS NULL OR previous_price IS NULL THEN
    RETURN NULL;
  END IF;

  RETURN today_price / previous_price - 1;
END //

DELIMITER ;


-- -------------------------------------------------------------
-- 2. event_returns: every event with its abnormal return
--
--    abnormal return = stock's move - XBI's move
--
--    All the queries build on this view.
-- -------------------------------------------------------------
CREATE VIEW event_returns AS
SELECT
  e.event_id,
  e.company_id,
  c.name        AS company_name,
  stock.ticker,
  e.event_type,
  e.outcome,
  e.trading_day,
  e.nct_number,
  e.fda_action_id,

  daily_return(stock.security_id, e.trading_day) AS stock_return,
  daily_return(xbi.security_id,   e.trading_day) AS xbi_return,

  daily_return(stock.security_id, e.trading_day)
    - daily_return(xbi.security_id, e.trading_day) AS abnormal_return

FROM events e
JOIN companies  c     ON c.company_id     = e.company_id
JOIN securities stock ON stock.company_id = e.company_id
JOIN securities xbi   ON xbi.ticker       = 'XBI';


-- -------------------------------------------------------------
-- 3. compute_abnormal_returns: a readable report
--
--    Shows moves as percentages, biggest first.
--    CALL compute_abnormal_returns(NULL);  -- every event
--    CALL compute_abnormal_returns(1);     -- just event 1
-- -------------------------------------------------------------
DELIMITER //

CREATE PROCEDURE compute_abnormal_returns(IN which_event INT)
BEGIN
  SELECT
    event_id,
    company_name,
    event_type,
    outcome,
    trading_day,
    ROUND(stock_return    * 100, 2) AS stock_pct,
    ROUND(xbi_return      * 100, 2) AS xbi_pct,
    ROUND(abnormal_return * 100, 2) AS abnormal_pct,
    IF(abnormal_return IS NULL, 'missing price', 'ok') AS status
  FROM event_returns
  WHERE which_event IS NULL
     OR event_id = which_event
  ORDER BY ABS(abnormal_return) DESC;
END //

DELIMITER ;


-- -------------------------------------------------------------
-- Try it
-- -------------------------------------------------------------
CALL compute_abnormal_returns(NULL);

-- Expected with the test data (biggest moves first):
--   event  company            type           outcome   stock    xbi     abnormal  status
--   2      Beta Therapeutics  fda_decision   rejected  -45.00   -0.98   -44.02    ok
--   1      Acme Bio           fda_decision   approved   11.97    1.99     9.98    ok
--   5      Gamma Pharma       trial_readout  negative   -8.20   -0.98    -7.22    ok
--   4      Gamma Pharma       fda_decision   approved    0.99   -0.98     1.97    ok
--   6      Gamma Pharma       fda_decision   approved    0.39    0.49    -0.10    ok
--   3      Acme Bio           trial_readout  positive   NULL     NULL     NULL    missing price
