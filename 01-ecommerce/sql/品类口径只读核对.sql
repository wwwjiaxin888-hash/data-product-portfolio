-- DBeaver中连接项目MySQL后，逐条运行；本文件无CREATE/DROP/TRUNCATE/INSERT/UPDATE/DELETE。
-- 1 当前库与时区；若不是dw_project01，请在DBeaver先选择项目库。
SELECT DATABASE() AS current_database, @@session.time_zone AS session_timezone;
-- 2 确认实际对象（可据结果决定后续SELECT是否能运行）。
SHOW TABLES FROM dw_project01 LIKE 'ads_category';
SHOW TABLES FROM dw_project01 LIKE 'dwd_user_behavior';
-- 3 检查实际ADS当前值，不重建表。
SELECT * FROM dw_project01.ads_category ORDER BY category_id;
-- 4 检查DWD范围。预期10000行、880用户，日期2024-11-25至12-04。
SELECT COUNT(*) AS rows_count, COUNT(DISTINCT user_id) AS all_users,
       MIN(date) AS min_date, MAX(date) AS max_date
FROM dw_project01.dwd_user_behavior;
-- 5 全周期去重口径；1004预期view_users=542、buy_users=127、cvr_pct=23.4。
SELECT
    category_id,
    COUNT(DISTINCT CASE WHEN behavior_type='pv' THEN user_id END) AS view_users,
    COUNT(DISTINCT CASE WHEN behavior_type='buy' THEN user_id END) AS buy_users,
    ROUND(
        100.0 * COUNT(DISTINCT CASE WHEN behavior_type='buy' THEN user_id END)
        / NULLIF(COUNT(DISTINCT CASE WHEN behavior_type='pv' THEN user_id END), 0),
        1
    ) AS cvr_pct
FROM dw_project01.dwd_user_behavior
GROUP BY category_id
ORDER BY buy_users DESC;
-- 6 原脚本的每日人数累计口径，作为对照；1004预期929、137、14.7。
SELECT category_id,SUM(view_users) AS view_user_days,SUM(buy_users) AS buy_user_days,
       ROUND(100.0*SUM(buy_users)/NULLIF(SUM(view_users),0),1) AS user_day_ratio_pct
FROM dw_project01.dws_category_day GROUP BY category_id ORDER BY category_id;
-- 如果出现表不存在：记录该结果即可，不要为完成核对执行整份建库脚本。
