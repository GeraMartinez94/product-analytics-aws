-- Retencion por cohorte semanal de signup: % de usuarios que vuelven el dia N (D1, D7, D14, D30).
-- "Vuelve" = tiene cualquier evento exactamente N dias despues de su signup.
WITH cohort AS (
    SELECT user_id, CAST(MIN(event_ts) AS DATE) AS signup_date
    FROM events
    WHERE event_name = 'signup'
    GROUP BY user_id
),
activity AS (
    SELECT DISTINCT user_id, CAST(event_ts AS DATE) AS activity_date FROM events
),
returned AS (
    SELECT
        c.user_id,
        DATE_TRUNC('week', c.signup_date) AS cohort_week,
        DATE_DIFF('day', c.signup_date, a.activity_date) AS day_n
    FROM cohort c
    JOIN activity a ON a.user_id = c.user_id
)
SELECT
    cohort_week,
    COUNT(DISTINCT user_id) FILTER (WHERE day_n = 0)                              AS cohort_size,
    ROUND(100.0 * COUNT(DISTINCT user_id) FILTER (WHERE day_n = 1)
          / COUNT(DISTINCT user_id) FILTER (WHERE day_n = 0), 1)                  AS d1_pct,
    ROUND(100.0 * COUNT(DISTINCT user_id) FILTER (WHERE day_n = 7)
          / COUNT(DISTINCT user_id) FILTER (WHERE day_n = 0), 1)                  AS d7_pct,
    ROUND(100.0 * COUNT(DISTINCT user_id) FILTER (WHERE day_n = 14)
          / COUNT(DISTINCT user_id) FILTER (WHERE day_n = 0), 1)                  AS d14_pct,
    ROUND(100.0 * COUNT(DISTINCT user_id) FILTER (WHERE day_n = 30)
          / COUNT(DISTINCT user_id) FILTER (WHERE day_n = 0), 1)                  AS d30_pct
FROM returned
GROUP BY cohort_week
ORDER BY cohort_week;
