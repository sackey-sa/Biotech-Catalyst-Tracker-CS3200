-- title: How fast does news reach the SEC?
-- question: For events backed by an SEC filing, how many hours passed between the news and the filing's acceptance, and did after-hours news get filed more slowly?
-- After-hours = news at or after 20:00 UTC (4pm New York, standard time), which trades the next day.
SELECT e.event_type,
       CASE WHEN TIME(e.event_timestamp) >= '20:00:00' THEN 'after close' ELSE 'before/during market' END AS news_timing,
       COUNT(*)                                                                   AS events,
       ROUND(AVG(TIMESTAMPDIFF(MINUTE, e.event_timestamp, f.acceptance_timestamp)) / 60, 1) AS avg_hours_to_filing,
       ROUND(MAX(TIMESTAMPDIFF(MINUTE, e.event_timestamp, f.acceptance_timestamp)) / 60, 1) AS slowest_hours,
       SUM(f.filing_date > DATE(e.event_timestamp))                               AS filed_next_day_or_later
FROM events e
JOIN filings f ON f.accession_number = e.accession_number
WHERE f.acceptance_timestamp IS NOT NULL
GROUP BY e.event_type, news_timing
ORDER BY e.event_type, news_timing;
