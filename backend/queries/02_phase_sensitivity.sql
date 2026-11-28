-- title: Do later-stage trials move stocks more?
-- question: For trial readouts, how big is the typical stock reaction (in either direction) at each clinical phase, and what share of readouts were positive?
-- Absolute abnormal return measures how much news there was, regardless of direction.
SELECT t.phase,
       COUNT(*)                                                    AS readouts,
       ROUND(AVG(ABS(r.abnormal_return_1d)) * 100, 2)              AS avg_size_of_move_pct,
       ROUND(100 * SUM(e.outcome = 'positive') / COUNT(*), 1)      AS pct_positive,
       ROUND(AVG(t.enrollment))                                    AS avg_enrollment
FROM events e
JOIN trials t         ON t.nct_number = e.nct_number
JOIN event_returns r  ON r.event_id = e.event_id
WHERE e.event_type = 'trial_readout'
GROUP BY t.phase
ORDER BY avg_size_of_move_pct DESC;
