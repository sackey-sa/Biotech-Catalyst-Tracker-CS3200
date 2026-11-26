-- title: FDA approvals vs. remaining pipeline
-- question: For each FDA approval, how did the stock do against XBI over the following week, and how many other trials did the company still have running at the time?
-- The correlated subquery counts trials that started before the decision and had not completed by then.
SELECT c.name                                       AS company,
       s.ticker,
       COALESCE(d.brand_name, d.active_ingredient)  AS drug,
       fa.application_number,
       fa.action_date,
       ROUND(r.abnormal_return_1d * 100, 2)         AS abnormal_1d_pct,
       ROUND(r.abnormal_return_5d * 100, 2)         AS abnormal_5d_pct,
       (SELECT COUNT(*)
          FROM trials t
         WHERE t.company_id = c.company_id
           AND t.start_date <= fa.action_date
           AND (t.completion_date IS NULL OR t.completion_date > fa.action_date)) AS trials_running_at_decision
FROM fda_actions fa
JOIN events e         ON e.fda_action_id = fa.fda_action_id
JOIN companies c      ON c.company_id = fa.company_id
JOIN securities s     ON s.company_id = c.company_id
JOIN drugs d          ON d.drug_id = fa.drug_id
JOIN event_returns r  ON r.event_id = e.event_id
WHERE e.outcome = 'approved'
ORDER BY abnormal_5d_pct DESC;
