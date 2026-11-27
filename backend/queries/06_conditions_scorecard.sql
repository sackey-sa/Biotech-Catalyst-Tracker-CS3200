-- title: Disease areas scorecard
-- question: For each disease area, how many trials and companies are working on it, how many readouts have there been, and what was the average market reaction to those readouts?
-- Uses a derived table of readouts per trial, so trials without a readout still count toward the totals.
SELECT co.condition_name,
       COUNT(DISTINCT t.nct_number)                            AS trials,
       COUNT(DISTINCT t.company_id)                            AS companies,
       COUNT(rd.event_id)                                      AS readouts,
       SUM(rd.outcome = 'positive')                            AS positive_readouts,
       ROUND(AVG(rd.abnormal_return_1d) * 100, 2)              AS avg_readout_abnormal_1d_pct
FROM conditions co
JOIN trial_conditions tc ON tc.condition_id = co.condition_id
JOIN trials t            ON t.nct_number = tc.nct_number
LEFT JOIN (
    SELECT e.event_id, e.nct_number, e.outcome, r.abnormal_return_1d
    FROM events e
    JOIN event_returns r ON r.event_id = e.event_id
    WHERE e.event_type = 'trial_readout'
) rd ON rd.nct_number = t.nct_number
GROUP BY co.condition_id, co.condition_name
ORDER BY trials DESC, readouts DESC;
