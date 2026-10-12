-- Funnel de conversion: cuantos usuarios llegan a cada paso (y a que % del paso anterior).
-- Una fila por usuario con el primer timestamp de cada paso, luego se cuenta.
WITH per_user AS (
    SELECT
        user_id,
        MIN(event_ts) FILTER (WHERE event_name = 'signup')              AS signup_ts,
        MIN(event_ts) FILTER (WHERE event_name = 'onboarding_complete') AS onboarding_ts,
        MIN(event_ts) FILTER (WHERE event_name = 'feature_used')        AS feature_ts,
        MIN(event_ts) FILTER (WHERE event_name = 'add_to_cart')         AS cart_ts,
        MIN(event_ts) FILTER (WHERE event_name = 'purchase')            AS purchase_ts
    FROM events
    GROUP BY user_id
),
steps AS (
    SELECT 1 AS step_no, 'signup' AS step, COUNT(*) AS users FROM per_user WHERE signup_ts IS NOT NULL
    UNION ALL SELECT 2, 'onboarding_complete', COUNT(*) FROM per_user WHERE onboarding_ts IS NOT NULL
    UNION ALL SELECT 3, 'feature_used',        COUNT(*) FROM per_user WHERE feature_ts IS NOT NULL
    UNION ALL SELECT 4, 'add_to_cart',         COUNT(*) FROM per_user WHERE cart_ts IS NOT NULL
    UNION ALL SELECT 5, 'purchase',            COUNT(*) FROM per_user WHERE purchase_ts IS NOT NULL
)
SELECT
    step_no,
    step,
    users,
    ROUND(100.0 * users / FIRST_VALUE(users) OVER (ORDER BY step_no), 1)  AS pct_of_signup,
    ROUND(100.0 * users / LAG(users) OVER (ORDER BY step_no), 1)          AS pct_of_prev_step
FROM steps
ORDER BY step_no;
