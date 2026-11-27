-- title: Market reaction by catalyst type and outcome
-- question: For each kind of catalyst (FDA decision or trial readout) and each outcome, how many events were there, and how much did the stock beat or trail the XBI biotech index on the day and over the following week?
-- Abnormal return = stock return minus XBI return, from the close before the news.
-- Uses the event_returns view (backend/sql/views.sql), which joins events -> securities -> prices twice: once for the stock, once for XBI.
SELECT r.event_type,
       r.outcome,
       COUNT(*)                                   AS events,
       ROUND(AVG(r.stock_return_1d) * 100, 2)     AS avg_stock_move_1d_pct,
       ROUND(AVG(r.abnormal_return_1d) * 100, 2)  AS avg_abnormal_1d_pct,
       ROUND(AVG(r.abnormal_return_5d) * 100, 2)  AS avg_abnormal_5d_pct,
       ROUND(MIN(r.abnormal_return_1d) * 100, 2)  AS worst_1d_pct,
       ROUND(MAX(r.abnormal_return_1d) * 100, 2)  AS best_1d_pct
FROM event_returns r
GROUP BY r.event_type, r.outcome
ORDER BY r.event_type, avg_abnormal_1d_pct DESC;
