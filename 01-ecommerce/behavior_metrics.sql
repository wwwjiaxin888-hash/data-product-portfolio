-- Each behavior counts distinct users independently within a scope.
WITH scoped_events AS (
    SELECT 'all' AS scope, user_id, behavior_type FROM events
    UNION ALL
    SELECT 'category:' || category_id, user_id, behavior_type FROM events
),
counts AS (
    SELECT
        scope,
        COUNT(DISTINCT user_id) AS active_users,
        COUNT(DISTINCT CASE WHEN behavior_type = 'pv' THEN user_id END) AS view_users,
        COUNT(DISTINCT CASE WHEN behavior_type = 'fav' THEN user_id END) AS favorite_users,
        COUNT(DISTINCT CASE WHEN behavior_type = 'cart' THEN user_id END) AS cart_users,
        COUNT(DISTINCT CASE WHEN behavior_type = 'buy' THEN user_id END) AS buy_users
    FROM scoped_events
    GROUP BY scope
)
SELECT
    *,
    ROUND(100.0 * buy_users / NULLIF(view_users, 0), 2) AS buy_to_view_pct
FROM counts
ORDER BY scope;
