-- DAU, MAU (ventana movil de 30 dias) y stickiness = DAU / MAU.
-- Solo se reportan fechas con 30 dias completos de historia.
WITH daily AS (
    SELECT DISTINCT CAST(event_ts AS DATE) AS activity_date, user_id FROM events
),
dates AS (
    SELECT DISTINCT activity_date AS d FROM daily
),
bounds AS (SELECT MIN(d) AS first_day FROM dates)
SELECT
    d.d AS activity_date,
    COUNT(DISTINCT x.user_id) FILTER (WHERE x.activity_date = d.d)             AS dau,
    COUNT(DISTINCT x.user_id)                                                  AS mau_30d,
    ROUND(100.0 * COUNT(DISTINCT x.user_id) FILTER (WHERE x.activity_date = d.d)
          / COUNT(DISTINCT x.user_id), 1)                                      AS stickiness_pct
FROM dates d
CROSS JOIN bounds b
JOIN daily x ON DATE_DIFF('day', x.activity_date, d.d) BETWEEN 0 AND 29
WHERE DATE_DIFF('day', b.first_day, d.d) >= 29
GROUP BY d.d
ORDER BY d.d;
