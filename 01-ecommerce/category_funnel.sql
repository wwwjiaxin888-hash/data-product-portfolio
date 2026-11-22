-- Require strictly increasing timestamps within a user and category.
WITH behavior_counts AS (
    SELECT
        category_id,
        COUNT(DISTINCT CASE WHEN behavior_type = 'pv' THEN user_id END) AS view_users,
        COUNT(DISTINCT CASE WHEN behavior_type = 'cart' THEN user_id END) AS cart_users,
        COUNT(DISTINCT CASE WHEN behavior_type = 'buy' THEN user_id END) AS buy_users
    FROM events
    GROUP BY category_id
),
first_view AS (
    SELECT user_id, category_id, MIN(event_ts) AS view_ts
    FROM events
    WHERE behavior_type = 'pv'
    GROUP BY user_id, category_id
),
first_cart AS (
    SELECT v.user_id, v.category_id, MIN(e.event_ts) AS cart_ts
    FROM first_view AS v
    JOIN events AS e
      ON e.user_id = v.user_id
     AND e.category_id = v.category_id
     AND e.behavior_type = 'cart'
     AND e.event_ts > v.view_ts
    GROUP BY v.user_id, v.category_id
),
completed_journeys AS (
    SELECT c.user_id, c.category_id
    FROM first_cart AS c
    WHERE EXISTS (
        SELECT 1
        FROM events AS e
        WHERE e.user_id = c.user_id
          AND e.category_id = c.category_id
          AND e.behavior_type = 'buy'
          AND e.event_ts > c.cart_ts
    )
),
ordered_counts AS (
    SELECT
        v.category_id,
        COUNT(c.user_id) AS cart_after_view,
        COUNT(j.user_id) AS buy_after_cart
    FROM first_view AS v
    LEFT JOIN first_cart AS c
      ON c.user_id = v.user_id AND c.category_id = v.category_id
    LEFT JOIN completed_journeys AS j
      ON j.user_id = v.user_id AND j.category_id = v.category_id
    GROUP BY v.category_id
)
SELECT
    b.category_id,
    b.view_users,
    b.cart_users,
    b.buy_users,
    ROUND(100.0 * b.buy_users / NULLIF(b.view_users, 0), 2) AS broad_rate_pct,
    COALESCE(o.cart_after_view, 0) AS cart_after_view,
    COALESCE(o.buy_after_cart, 0) AS buy_after_cart,
    ROUND(100.0 * COALESCE(o.buy_after_cart, 0) / NULLIF(b.view_users, 0), 2) AS ordered_rate_pct
FROM behavior_counts AS b
LEFT JOIN ordered_counts AS o ON o.category_id = b.category_id
ORDER BY b.category_id;
