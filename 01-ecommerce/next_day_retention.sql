-- First seen is defined within the sample's observation window.
WITH cohorts AS (
    SELECT user_id, MIN(event_date) AS cohort_date
    FROM events
    GROUP BY user_id
),
observations AS (
    SELECT
        cohort_date,
        date(cohort_date, '+1 day') <= (SELECT MAX(event_date) FROM events) AS is_observed,
        EXISTS (
            SELECT 1
            FROM events
            WHERE events.user_id = cohorts.user_id
              AND events.event_date = date(cohorts.cohort_date, '+1 day')
        ) AS returned
    FROM cohorts
)
SELECT
    cohort_date,
    COUNT(*) AS cohort_users,
    CASE WHEN is_observed THEN SUM(returned) END AS returned_next_day,
    CASE WHEN is_observed THEN ROUND(100.0 * SUM(returned) / COUNT(*), 2) END AS next_day_pct
FROM observations
GROUP BY cohort_date, is_observed
ORDER BY cohort_date;
