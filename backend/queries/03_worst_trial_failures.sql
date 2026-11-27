-- title: Biggest drops after failed trials
-- question: Which negative or mixed trial readouts caused the largest one-day drops relative to XBI, and what disease and drug were being tested?
SELECT c.name                                                   AS company,
       s.ticker,
       e.trading_day,
       t.nct_number,
       t.phase,
       GROUP_CONCAT(DISTINCT co.condition_name SEPARATOR '; ')  AS conditions,
       GROUP_CONCAT(DISTINCT d.active_ingredient SEPARATOR '; ') AS drugs,
       e.outcome,
       ROUND(r.abnormal_return_1d * 100, 2)                     AS abnormal_1d_pct
FROM events e
JOIN companies c              ON c.company_id = e.company_id
JOIN securities s             ON s.company_id = c.company_id
JOIN trials t                 ON t.nct_number = e.nct_number
JOIN trial_conditions tc      ON tc.nct_number = t.nct_number
JOIN conditions co            ON co.condition_id = tc.condition_id
JOIN trial_drugs td           ON td.nct_number = t.nct_number
JOIN drugs d                  ON d.drug_id = td.drug_id
JOIN event_returns r          ON r.event_id = e.event_id
WHERE e.outcome IN ('negative', 'mixed')
GROUP BY e.event_id, c.name, s.ticker, e.trading_day, t.nct_number, t.phase, e.outcome, r.abnormal_return_1d
ORDER BY r.abnormal_return_1d
LIMIT 10;
