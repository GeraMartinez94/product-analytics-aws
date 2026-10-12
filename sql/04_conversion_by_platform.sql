-- Conversion signup -> purchase por plataforma: donde esta el problema, web o mobile?
WITH per_user AS (
    SELECT
        user_id,
        MAX(platform) AS platform,
        MAX(CASE WHEN event_name = 'purchase' THEN 1 ELSE 0 END) AS purchased
    FROM events
    GROUP BY user_id
)
SELECT
    platform,
    COUNT(*)                                    AS users,
    SUM(purchased)                              AS buyers,
    ROUND(100.0 * SUM(purchased) / COUNT(*), 2) AS conversion_pct
FROM per_user
GROUP BY platform
ORDER BY conversion_pct DESC;
