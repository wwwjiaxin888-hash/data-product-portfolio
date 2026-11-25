-- SQLite 3.30+. Load the cleaned event log with run-ordered-funnel.py.
-- Each row is one deduplicated event with a Unix-second timestamp.
-- entity_id is the item by default, or the category in the sensitivity check.
WITH
observation AS (
    SELECT MAX(ts) AS last_observed_ts FROM events
),
first_views AS (
    SELECT user_id, entity_id, category_id, MIN(ts) AS view_ts
    FROM events
    WHERE behavior = 'pv'
    GROUP BY user_id, entity_id, category_id
),
eligible_views AS (
    SELECT v.*, v.view_ts + :window_seconds AS deadline
    FROM first_views v CROSS JOIN observation o
    WHERE v.view_ts + :window_seconds <= o.last_observed_ts
),
first_carts AS (
    SELECT v.*,
        (SELECT MIN(e.ts) FROM events e
         WHERE e.user_id = v.user_id AND e.entity_id = v.entity_id
           AND e.category_id = v.category_id AND e.behavior = 'cart'
           AND e.ts > v.view_ts AND e.ts <= v.deadline) AS cart_ts
    FROM eligible_views v
),
paths AS (
    SELECT c.*,
        (SELECT MIN(e.ts) FROM events e
         WHERE e.user_id = c.user_id AND e.entity_id = c.entity_id
           AND e.category_id = c.category_id AND e.behavior = 'buy'
           AND e.ts > c.cart_ts AND e.ts <= c.deadline) AS ordered_buy_ts,
        (SELECT MIN(e.ts) FROM events e
         WHERE e.user_id = c.user_id AND e.entity_id = c.entity_id
           AND e.category_id = c.category_id AND e.behavior = 'buy'
           AND e.ts > c.view_ts AND e.ts <= c.deadline) AS any_buy_ts
    FROM first_carts c
),
breakdown AS (
    SELECT 'ALL' AS category, COUNT(*) AS viewed_pairs,
           COUNT(cart_ts) AS cart_pairs, COUNT(ordered_buy_ts) AS ordered_buy_pairs,
           COUNT(any_buy_ts) AS buy_after_view_pairs
    FROM paths
    UNION ALL
    SELECT category_id, COUNT(*), COUNT(cart_ts), COUNT(ordered_buy_ts), COUNT(any_buy_ts)
    FROM paths
    GROUP BY category_id
)
SELECT category, viewed_pairs, cart_pairs, ordered_buy_pairs, buy_after_view_pairs,
       buy_after_view_pairs - ordered_buy_pairs AS buy_without_ordered_cart_pairs,
       ROUND(100.0 * cart_pairs / NULLIF(viewed_pairs, 0), 2) AS view_to_cart_pct,
       ROUND(100.0 * ordered_buy_pairs / NULLIF(cart_pairs, 0), 2) AS cart_to_buy_pct,
       ROUND(100.0 * ordered_buy_pairs / NULLIF(viewed_pairs, 0), 2) AS full_path_pct
FROM breakdown
ORDER BY category <> 'ALL', category;
