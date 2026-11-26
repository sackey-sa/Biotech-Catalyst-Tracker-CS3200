-- =============================================================
-- 04_tests.sql
-- Checks the calculations and queries against answers worked
-- out by hand from 01_test_data.sql.
--
-- How to run:
--   1. Run 01_test_data.sql
--   2. Run 02_calculations.sql
--   3. Run this file. Every row should say PASS.
--
-- Never run 01_test_data.sql on the real database:
-- the fake companies would show up in real results.
-- =============================================================

USE biotech_catalyst;

SELECT
  test,
  expected,
  actual,
  IF(actual <=> expected, 'PASS', 'FAIL') AS result
FROM (

  -- ---------------- Calculations ----------------

  -- 1. One day's return: XBI, Monday March 11 vs Friday March 8
  --    92.10 / 90.30 - 1 = 1.99%
  SELECT 'XBI daily return is 1.99%' AS test,
         '1.99' AS expected,
         CAST(ROUND(daily_return(3, '2024-03-11') * 100, 2) AS CHAR) AS actual

  UNION ALL

  -- 2. Weekend skip: ACME 24.50 / 21.88 - 1 = 11.97%
  SELECT 'Monday compares to Friday (ACME +11.97%)',
         '11.97',
         CAST(ROUND(stock_return * 100, 2) AS CHAR)
  FROM event_returns WHERE event_id = 1

  UNION ALL

  -- 3. Good news: 11.97% - 1.99% = 9.98%
  SELECT 'Acme approval abnormal return is +9.98%',
         '9.98',
         CAST(ROUND(abnormal_return * 100, 2) AS CHAR)
  FROM event_returns WHERE event_id = 1

  UNION ALL

  -- 4. Bad news: -45.00% - (-0.98%) = -44.02%
  SELECT 'Beta rejection abnormal return is -44.02%',
         '-44.02',
         CAST(ROUND(abnormal_return * 100, 2) AS CHAR)
  FROM event_returns WHERE event_id = 2

  UNION ALL

  -- 5. Missing price: no number is made up
  SELECT 'Event with no price returns NULL',
         'NULL',
         IFNULL(CAST(abnormal_return AS CHAR), 'NULL')
  FROM event_returns WHERE event_id = 3

  UNION ALL

  -- 6. No double counting: one row per event
  SELECT 'One result row per event',
         CAST((SELECT COUNT(*) FROM events) AS CHAR),
         CAST(COUNT(*) AS CHAR)
  FROM event_returns

  UNION ALL

  -- ---------------- Queries ----------------

  -- 7. Query 2: bad news average move size = (44.02 + 7.22) / 2 = 25.62%
  SELECT 'Query 2: bad news moves 25.62% on average',
         '25.62',
         CAST(ROUND(AVG(ABS(abnormal_return)) * 100, 2) AS CHAR)
  FROM event_returns
  WHERE outcome IN ('rejected', 'negative')
    AND abnormal_return IS NOT NULL

  UNION ALL

  -- 8. Query 3: Gamma Pharma has 3 drugs
  SELECT 'Query 3: Gamma Pharma has 3 drugs',
         '3',
         CAST(COUNT(DISTINCT td.drug_id) AS CHAR)
  FROM trials t
  JOIN trial_drugs td ON td.nct_number = t.nct_number
  WHERE t.company_id = 3

  UNION ALL

  -- 9. Query 5: Gamma Pharma has 2 Phase 3 trials
  SELECT 'Query 5: Gamma Pharma has 2 Phase 3 trials',
         '2',
         CAST(COUNT(*) AS CHAR)
  FROM trials
  WHERE company_id = 3 AND phase = 'PHASE3'

  UNION ALL

  -- 10. Query 6: three events beat twice XBI's average move (2.00%)
  SELECT 'Query 6: 3 events beat twice the sector move',
         '3',
         CAST(COUNT(*) AS CHAR)
  FROM event_returns er
  WHERE ABS(er.abnormal_return) > 2 * (
    SELECT AVG(ABS(daily_return(p.security_id, p.trade_date)))
    FROM prices p
    JOIN securities s ON s.security_id = p.security_id
    WHERE s.ticker = 'XBI'
  )

) AS checks;

-- Expected: ten rows, all PASS.
