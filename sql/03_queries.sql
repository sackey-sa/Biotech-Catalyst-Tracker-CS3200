-- =============================================================
-- 03_queries.sql
-- The six questions our database answers.
-- Run after 02_calculations.sql. Most queries build on the
-- event_returns view; Query 1 shows the full price math by hand.
--
-- "Abnormal return" = the stock's move minus XBI's move that day:
-- the part of the move caused by the company's own news.
-- "Move size" = the abnormal return ignoring up or down, so a
-- big drop and a big jump both count as big.
-- =============================================================

USE biotech_catalyst;


-- -------------------------------------------------------------
-- QUERY 1
-- Which FDA approvals produced the largest abnormal returns?
--
-- Calculates every daily return from prices with LAG (today's
-- price vs. the previous trading day's), then joins those returns
-- twice: once for the company's stock, once for XBI.
-- -------------------------------------------------------------
WITH daily_returns AS (
  SELECT
    security_id,
    trade_date,
    adjusted_close
      / LAG(adjusted_close) OVER (PARTITION BY security_id ORDER BY trade_date)
      - 1 AS daily_return
  FROM prices
)
SELECT
  c.name                                                 AS company,
  d.brand_name                                           AS drug,
  e.trading_day,
  ROUND(stock_day.daily_return * 100, 2)                 AS stock_pct,
  ROUND(xbi_day.daily_return   * 100, 2)                 AS xbi_pct,
  ROUND((stock_day.daily_return - xbi_day.daily_return) * 100, 2) AS abnormal_pct
FROM events e
JOIN fda_actions   fa        ON fa.fda_action_id = e.fda_action_id
JOIN drugs         d         ON d.drug_id        = fa.drug_id
JOIN companies     c         ON c.company_id     = e.company_id
JOIN securities    stock     ON stock.company_id = e.company_id
JOIN securities    xbi       ON xbi.ticker       = 'XBI'
JOIN daily_returns stock_day ON stock_day.security_id = stock.security_id
                            AND stock_day.trade_date  = e.trading_day
JOIN daily_returns xbi_day   ON xbi_day.security_id   = xbi.security_id
                            AND xbi_day.trade_date    = e.trading_day
WHERE e.outcome = 'approved'
ORDER BY abnormal_pct DESC;

-- Expected with test data:
--   company       drug       trading_day  stock_pct  xbi_pct  abnormal_pct
--   Acme Bio      Acmezumab  2024-03-11      11.97     1.99          9.98
--   Gamma Pharma  Gammanib   2024-03-12       0.99    -0.98          1.97
--   Gamma Pharma  Gammavir   2024-03-13       0.39     0.49         -0.10


-- -------------------------------------------------------------
-- QUERY 2
-- Does bad news move stocks more than good news?
--
-- Groups events into good news (approved, positive results) and
-- bad news (rejected, negative results), then compares them.
-- -------------------------------------------------------------
SELECT
  CASE
    WHEN outcome IN ('approved', 'positive') THEN 'good news'
    WHEN outcome IN ('rejected', 'negative') THEN 'bad news'
    ELSE 'mixed'
  END                                      AS news_type,
  COUNT(*)                                 AS events,
  ROUND(AVG(abnormal_return) * 100, 2)     AS avg_abnormal_pct,
  ROUND(AVG(ABS(abnormal_return)) * 100, 2) AS avg_move_size_pct
FROM event_returns
WHERE abnormal_return IS NOT NULL
GROUP BY news_type
ORDER BY avg_move_size_pct DESC;

-- Expected with test data:
--   news_type  events  avg_abnormal_pct  avg_move_size_pct
--   bad news        2            -25.62              25.62
--   good news       3              3.95               4.02


-- -------------------------------------------------------------
-- QUERY 3
-- Do companies with fewer drugs swing harder?
--
-- A subquery counts each company's drugs (through its trials),
-- then compares that to how big its stock moves were.
-- -------------------------------------------------------------
SELECT
  c.name                                       AS company,
  drug_counts.drugs,
  COUNT(er.event_id)                           AS events,
  ROUND(AVG(ABS(er.abnormal_return)) * 100, 2) AS avg_move_size_pct
FROM companies c
JOIN (
  SELECT t.company_id, COUNT(DISTINCT td.drug_id) AS drugs
  FROM trials t
  JOIN trial_drugs td ON td.nct_number = t.nct_number
  GROUP BY t.company_id
) AS drug_counts         ON drug_counts.company_id = c.company_id
JOIN event_returns er    ON er.company_id          = c.company_id
WHERE er.abnormal_return IS NOT NULL
GROUP BY c.company_id, c.name, drug_counts.drugs
ORDER BY drug_counts.drugs, avg_move_size_pct DESC;

-- Expected with test data:
--   company            drugs  events  avg_move_size_pct
--   Beta Therapeutics      1       1              44.02
--   Acme Bio               1       1               9.98
--   Gamma Pharma           3       3               3.10


-- -------------------------------------------------------------
-- QUERY 4
-- How do stock moves differ by trial phase?
--
-- Trial results link to their trial directly. FDA approvals reach
-- their trial through the drug: events -> fda_actions -> drugs ->
-- trial_drugs -> trials. DISTINCT keeps each event counted once
-- per phase, even if a drug was in several trials.
-- -------------------------------------------------------------
SELECT
  phase,
  COUNT(*)                                  AS events,
  ROUND(AVG(ABS(abnormal_return)) * 100, 2) AS avg_move_size_pct
FROM (
  SELECT DISTINCT
    er.event_id,
    t.phase,
    er.abnormal_return
  FROM event_returns er
  LEFT JOIN fda_actions fa ON fa.fda_action_id = er.fda_action_id
  LEFT JOIN trial_drugs td ON td.drug_id       = fa.drug_id
  JOIN trials t            ON t.nct_number     = COALESCE(er.nct_number, td.nct_number)
  WHERE er.abnormal_return IS NOT NULL
) AS event_phases
GROUP BY phase
ORDER BY phase;

-- Expected with test data:
--   phase   events  avg_move_size_pct
--   PHASE2       1               7.22
--   PHASE3       3               4.02
-- (Beta's rejection has no trial or FDA record, so it isn't counted.)


-- -------------------------------------------------------------
-- QUERY 5
-- Which companies have the most Phase 3 trials, and how big were
-- their stock moves?
--
-- A subquery counts each company's Phase 3 trials; a second
-- subquery finds its average move size.
-- -------------------------------------------------------------
SELECT
  c.name                    AS company,
  phase3.phase3_trials,
  (SELECT ROUND(AVG(ABS(er.abnormal_return)) * 100, 2)
   FROM event_returns er
   WHERE er.company_id = c.company_id
     AND er.abnormal_return IS NOT NULL) AS avg_move_size_pct
FROM companies c
JOIN (
  SELECT company_id, COUNT(*) AS phase3_trials
  FROM trials
  WHERE phase = 'PHASE3'
  GROUP BY company_id
) AS phase3 ON phase3.company_id = c.company_id
ORDER BY phase3.phase3_trials DESC, c.name;

-- Expected with test data:
--   company            phase3_trials  avg_move_size_pct
--   Gamma Pharma                   2               3.10
--   Acme Bio                       1               9.98
--   Beta Therapeutics              1              44.02


-- -------------------------------------------------------------
-- QUERY 6
-- Which events moved more than twice the sector's average daily move?
--
-- A subquery finds XBI's average daily move size; events whose
-- abnormal return is more than twice that are unusually large.
-- -------------------------------------------------------------
SELECT
  er.event_id,
  er.company_name,
  er.outcome,
  er.trading_day,
  ROUND(er.abnormal_return * 100, 2)   AS abnormal_pct,
  ROUND(2 * sector.avg_move * 100, 2)  AS threshold_pct
FROM event_returns er
CROSS JOIN (
  SELECT AVG(ABS(daily_return(p.security_id, p.trade_date))) AS avg_move
  FROM prices p
  JOIN securities s ON s.security_id = p.security_id
  WHERE s.ticker = 'XBI'
) AS sector
WHERE ABS(er.abnormal_return) > 2 * sector.avg_move
ORDER BY ABS(er.abnormal_return) DESC;

-- Expected with test data:
--   event_id  company_name       outcome   trading_day  abnormal_pct  threshold_pct
--          2  Beta Therapeutics  rejected  2024-03-12         -44.02           2.00
--          1  Acme Bio           approved  2024-03-11           9.98           2.00
--          5  Gamma Pharma       negative  2024-03-14          -7.22           2.00
