-- =============================================================
-- 03_queries.sql
-- Every question our database answers.
-- Run after 02_calculations.sql. Most queries build on the
-- event_returns view; Query 1 shows the full price math by hand.
-- Queries 7-12 also use the backend-only event_windows view
-- (5-day returns), created by:  python -m backend.setup_views
--
-- Each query starts with the same header:
--   -- QUERY N
--   -- title: Short name
--   -- question: The question in plain English
--   -- graded: yes | no
-- Only "graded: yes" queries go in the queries PDF.
--
-- "Abnormal return" = the stock's move minus XBI's move that day:
-- the part of the move caused by the company's own news.
-- "Move size" = the abnormal return ignoring up or down, so a
-- big drop and a big jump both count as big.
-- =============================================================

USE biotech_catalyst;


-- -------------------------------------------------------------
-- QUERY 1
-- title: Biggest reactions to FDA approvals
-- question: Which FDA approvals produced the largest abnormal returns?
-- graded: yes
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
-- title: Good news vs. bad news
-- question: Does bad news move stocks more than good news?
-- graded: yes
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
-- title: Fewer drugs, bigger swings?
-- question: Do companies with fewer drugs swing harder?
-- graded: yes
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
-- title: Stock moves by trial phase
-- question: How do stock moves differ by trial phase?
-- graded: yes
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
-- title: Phase 3 leaders and their moves
-- question: Which companies have the most Phase 3 trials, and how big were their stock moves?
-- graded: yes
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
-- title: Moves beyond twice the sector
-- question: Which events moved more than twice the sector's average daily move?
-- graded: yes
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


-- -------------------------------------------------------------
-- QUERY 7
-- title: Market reaction by catalyst type and outcome
-- question: For each kind of catalyst (FDA decision or trial readout) and each outcome, how many events were there, and how much did the stock beat or trail the XBI biotech index on the day and over the following week?
-- graded: no
--
-- 1-day returns come from event_returns; 5-day returns from the
-- backend's event_windows view. Events with a missing price are
-- counted but left out of the averages.
-- -------------------------------------------------------------
SELECT r.event_type,
       r.outcome,
       COUNT(*)                                  AS events,
       ROUND(AVG(r.stock_return) * 100, 2)       AS avg_stock_move_1d_pct,
       ROUND(AVG(r.abnormal_return) * 100, 2)    AS avg_abnormal_1d_pct,
       ROUND(AVG(w.abnormal_return_5d) * 100, 2) AS avg_abnormal_5d_pct,
       ROUND(MIN(r.abnormal_return) * 100, 2)    AS worst_1d_pct,
       ROUND(MAX(r.abnormal_return) * 100, 2)    AS best_1d_pct
FROM event_returns r
LEFT JOIN event_windows w ON w.event_id = r.event_id
GROUP BY r.event_type, r.outcome
ORDER BY r.event_type, avg_abnormal_1d_pct DESC;


-- -------------------------------------------------------------
-- QUERY 8
-- title: Do later-stage trials move stocks more?
-- question: For trial readouts, how big is the typical stock reaction (in either direction) at each clinical phase, and what share of readouts were positive?
-- graded: no
--
-- Absolute abnormal return measures how much news there was,
-- regardless of direction.
-- -------------------------------------------------------------
SELECT t.phase,
       COUNT(*)                                               AS readouts,
       ROUND(AVG(ABS(r.abnormal_return)) * 100, 2)            AS avg_size_of_move_pct,
       ROUND(100 * SUM(e.outcome = 'positive') / COUNT(*), 1) AS pct_positive,
       ROUND(AVG(t.enrollment))                               AS avg_enrollment
FROM events e
JOIN trials t         ON t.nct_number = e.nct_number
JOIN event_returns r  ON r.event_id = e.event_id
WHERE e.event_type = 'trial_readout'
GROUP BY t.phase
ORDER BY avg_size_of_move_pct DESC;


-- -------------------------------------------------------------
-- QUERY 9
-- title: Biggest drops after failed trials
-- question: Which negative or mixed trial readouts caused the largest one-day drops relative to XBI, and what disease and drug were being tested?
-- graded: no
--
-- Events with a missing price are skipped: MySQL sorts NULL first,
-- so they would otherwise top the list. Conditions and drugs are
-- LEFT JOINs, so a trial with none recorded still appears (with an
-- empty cell) instead of dropping out.
-- -------------------------------------------------------------
SELECT c.name                                                   AS company,
       s.ticker,
       e.trading_day,
       t.nct_number,
       t.phase,
       GROUP_CONCAT(DISTINCT co.condition_name SEPARATOR '; ')  AS conditions,
       GROUP_CONCAT(DISTINCT d.active_ingredient SEPARATOR '; ') AS drugs,
       e.outcome,
       ROUND(r.abnormal_return * 100, 2)                        AS abnormal_1d_pct
FROM events e
JOIN companies c              ON c.company_id = e.company_id
JOIN securities s             ON s.company_id = c.company_id
JOIN trials t                 ON t.nct_number = e.nct_number
LEFT JOIN trial_conditions tc ON tc.nct_number = t.nct_number
LEFT JOIN conditions co       ON co.condition_id = tc.condition_id
LEFT JOIN trial_drugs td      ON td.nct_number = t.nct_number
LEFT JOIN drugs d             ON d.drug_id = td.drug_id
JOIN event_returns r          ON r.event_id = e.event_id
WHERE e.outcome IN ('negative', 'mixed')
  AND r.abnormal_return IS NOT NULL
GROUP BY e.event_id, c.name, s.ticker, e.trading_day, t.nct_number, t.phase, e.outcome, r.abnormal_return
ORDER BY r.abnormal_return
LIMIT 10;


-- -------------------------------------------------------------
-- QUERY 10
-- title: FDA approvals vs. remaining pipeline
-- question: For each FDA approval, how did the stock do against XBI over the following week, and how many other trials did the company still have running at the time?
-- graded: no
--
-- The correlated subquery counts trials that started before the
-- decision and had not completed by then. 5-day returns come from
-- the backend's event_windows view.
-- -------------------------------------------------------------
SELECT c.name                                       AS company,
       s.ticker,
       COALESCE(d.brand_name, d.active_ingredient)  AS drug,
       fa.application_number,
       fa.action_date,
       ROUND(r.abnormal_return * 100, 2)            AS abnormal_1d_pct,
       ROUND(w.abnormal_return_5d * 100, 2)         AS abnormal_5d_pct,
       (SELECT COUNT(*)
          FROM trials t
         WHERE t.company_id = c.company_id
           AND t.start_date <= fa.action_date
           AND (t.completion_date IS NULL OR t.completion_date > fa.action_date)) AS trials_running_at_decision
FROM fda_actions fa
JOIN events e             ON e.fda_action_id = fa.fda_action_id
JOIN companies c          ON c.company_id = fa.company_id
JOIN securities s         ON s.company_id = c.company_id
JOIN drugs d              ON d.drug_id = fa.drug_id
JOIN event_returns r      ON r.event_id = e.event_id
LEFT JOIN event_windows w ON w.event_id = e.event_id
WHERE e.outcome = 'approved'
ORDER BY abnormal_5d_pct DESC;


-- -------------------------------------------------------------
-- QUERY 11
-- title: How fast does news reach the SEC?
-- question: For events backed by an SEC filing, how many hours passed between the news and the filing's acceptance, and did after-hours news get filed more slowly?
-- graded: no
--
-- After-hours = news at or after 4pm New York time, which trades the
-- next day. Timestamps are UTC, so the derived table converts them:
-- New York is UTC-4 during daylight saving time and UTC-5 otherwise
-- (4pm = 20:00 UTC in summer, 21:00 UTC in winter). US daylight saving
-- runs from the second Sunday of March at 07:00 UTC to the first Sunday
-- of November at 06:00 UTC. Worked out here because MySQL often has no
-- time zone tables, so CONVERT_TZ(..., 'America/New_York') returns NULL.
-- -------------------------------------------------------------
SELECT e.event_type,
       CASE WHEN TIME(ny.ny_time) >= '16:00:00' THEN 'after close' ELSE 'before/during market' END AS news_timing,
       COUNT(*)                                                                   AS events,
       ROUND(AVG(TIMESTAMPDIFF(MINUTE, e.event_timestamp, f.acceptance_timestamp)) / 60, 1) AS avg_hours_to_filing,
       ROUND(MAX(TIMESTAMPDIFF(MINUTE, e.event_timestamp, f.acceptance_timestamp)) / 60, 1) AS slowest_hours,
       SUM(f.filing_date > DATE(ny.ny_time))                                      AS filed_next_day_or_later
FROM events e
JOIN filings f ON f.accession_number = e.accession_number
JOIN (
  SELECT d.event_id,
         d.ts - INTERVAL IF(d.ts >= d.dst_start AND d.ts < d.dst_end, 4, 5) HOUR AS ny_time
  FROM (
    SELECT y.event_id,
           y.ts,
           TIMESTAMP(y.mar1 + INTERVAL ((8 - DAYOFWEEK(y.mar1)) % 7 + 7) DAY, '07:00:00') AS dst_start,
           TIMESTAMP(y.nov1 + INTERVAL ((8 - DAYOFWEEK(y.nov1)) % 7) DAY, '06:00:00')     AS dst_end
    FROM (
      SELECT event_id,
             event_timestamp                                         AS ts,
             MAKEDATE(YEAR(event_timestamp), 1) + INTERVAL 2 MONTH   AS mar1,
             MAKEDATE(YEAR(event_timestamp), 1) + INTERVAL 10 MONTH  AS nov1
      FROM events
    ) AS y
  ) AS d
) AS ny ON ny.event_id = e.event_id
WHERE f.acceptance_timestamp IS NOT NULL
GROUP BY e.event_type, news_timing
ORDER BY e.event_type, news_timing;


-- -------------------------------------------------------------
-- QUERY 12
-- title: Disease areas scorecard
-- question: For each disease area, how many trials and companies are working on it, how many readouts have there been, and what was the average market reaction to those readouts?
-- graded: no
--
-- Uses a derived table of readouts per trial, so trials without a
-- readout still count toward the totals.
-- -------------------------------------------------------------
SELECT co.condition_name,
       COUNT(DISTINCT t.nct_number)                AS trials,
       COUNT(DISTINCT t.company_id)                AS companies,
       COUNT(rd.event_id)                          AS readouts,
       SUM(rd.outcome = 'positive')                AS positive_readouts,
       ROUND(AVG(rd.abnormal_return) * 100, 2)     AS avg_readout_abnormal_1d_pct
FROM conditions co
JOIN trial_conditions tc ON tc.condition_id = co.condition_id
JOIN trials t            ON t.nct_number = tc.nct_number
LEFT JOIN (
    SELECT e.event_id, e.nct_number, e.outcome, r.abnormal_return
    FROM events e
    JOIN event_returns r ON r.event_id = e.event_id
    WHERE e.event_type = 'trial_readout'
) rd ON rd.nct_number = t.nct_number
GROUP BY co.condition_id, co.condition_name
ORDER BY trials DESC, readouts DESC;
