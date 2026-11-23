USE dw_project01;

DROP TABLE IF EXISTS ods_user_behavior;
#建ODS表，字段类型与原表完全一致
CREATE TABLE ods_user_behavior (
    user_id VARCHAR(50),
    item_id VARCHAR(50),
    category_id VARCHAR(50),
    behavior_type VARCHAR(20),
    timestamp VARCHAR(50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
select COUNT(*) from ods_user_behavior oub ;
#建立DWD层：清洗+补日期
USE dw_project01;
DROP TABLE IF EXISTS dwd_user_behavior;
CREATE TABLE dwd_user_behavior (
    user_id BIGINT,
    item_id BIGINT,
    category_id BIGINT,
    behavior_type VARCHAR(20),
    date DATE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
#插入清洗的数据
USE dw_project01;
TRUNCATE TABLE dwd_user_behavior;

INSERT INTO dwd_user_behavior#INSERT INTO 表名：把SELECT 查询出来的结果插入到表格中
SELECT
    CAST(TRIM(user_id) AS UNSIGNED) AS user_id,#CAST(值 AS 类型)：类型转换
    #`UNSIGNED` = 无符号整数（只能是≥0 的正数，适合用户 ID、商品 ID、品类 ID）
    CAST(TRIM(item_id) AS UNSIGNED) AS item_id,
    CAST(TRIM(category_id) AS UNSIGNED) AS category_id,
    TRIM(behavior_type) AS behavior_type,
    FROM_UNIXTIME(CAST(TRIM(timestamp) AS UNSIGNED), '%Y-%m-%d') AS date
     #用`FROM_UNIXTIME`把时间戳，转换成 `yyyy-MM-dd` 格式的日期
FROM (
    SELECT *,
        ROW_NUMBER() OVER(   #`ROW_NUMBER()`：在同一个分组内部，给每一行从 1 开始编号
            PARTITION BY TRIM(user_id),TRIM(item_id),TRIM(category_id),TRIM(behavior_type),TRIM(timestamp)
            #`PARTITION BY`：分组规则，**按 5 个原始字段分组**
#只要这 5 项全部一模一样 → 判定为重复行，分到同一个组
            ORDER BY TRIM(timestamp)
        ) AS rn
    FROM ods_user_behavior
    WHERE
        TRIM(user_id) REGEXP '^[0-9]+$'
         #REGEXP = 正则匹配
#`^[0-9]+$`：从头到尾全部是数字，不能有字母、逗号、空值、符号
        AND TRIM(item_id) REGEXP '^[0-9]+$'
        AND TRIM(category_id) REGEXP '^[0-9]+$'
        AND TRIM(timestamp) REGEXP '^[0-9]+$'
        AND behavior_type IN ('pv','cart','fav','buy')
) t
WHERE rn = 1;

SELECT COUNT(*) FROM dwd_user_behavior;
select MIN(date),MAX(date) from dwd_user_behavior dub ;
select COUNT(distinct user_id) from dwd_user_behavior dub ;
#DWS层建表
USE dw_project01;
CREATE TABLE dws_user_day (
    date DATE PRIMARY KEY,
    uv INT, 
    pv_users INT, 
    cart_users INT, 
    buy_users INT,
    pv_cnt INT, 
    buy_cnt INT
);
INSERT INTO dws_user_day
SELECT date,
COUNT(DISTINCT user_id) AS uv,
COUNT(DISTINCT CASE WHEN behavior_type='pv' THEN user_id END) AS pv_users,
COUNT(DISTINCT CASE WHEN behavior_type='cart' THEN user_id END) AS cart_users,
COUNT(DISTINCT CASE WHEN behavior_type='buy' THEN user_id END) AS buy_users,
SUM(behavior_type='pv') AS pv_cnt,
SUM(behavior_type='buy') AS buy_cnt
FROM dwd_user_behavior
GROUP BY date;
SELECT * FROM dws_user_day;
select SUM(buy_users) from dws_user_day;#此处不等于504，因为同一用户多天买会被重复计算，
#正是汇总表不能直接回答全局问题的典型例子
#构建 DWS 第二层：dws_category_day（按品类汇总表）
USE dw_project01;
DROP TABLE IF EXISTS dws_category_day;
CREATE TABLE dws_category_day (
    dt DATE, 
    category_id INT,
    view_users INT, 
    cart_users INT, 
    buy_users INT,
    PRIMARY KEY (dt, category_id)
);
#录入数据
INSERT INTO dws_category_day
SELECT date, category_id,
COUNT(DISTINCT CASE WHEN behavior_type='pv' THEN user_id END) AS view_users,
COUNT(DISTINCT CASE WHEN behavior_type='cart' THEN user_id END) AS cart_users,
COUNT(DISTINCT CASE WHEN behavior_type='buy' THEN user_id END) AS buy_users
FROM dwd_user_behavior
GROUP BY date, category_id;
select COUNT(*) from dws_category_day;

#任务三：构建ADS三张表
#ADS 表 1：ads_funnel 漏斗结果表
USE dw_project01;
CREATE TABLE ads_funnel as
#CTAS语法，执行后面 SELECT 查询，把查询返回的结果自动存成一张新表 ads_funnel
SELECT
COUNT(DISTINCT CASE WHEN behavior_type='pv' THEN user_id END) AS view_users,
COUNT(DISTINCT CASE WHEN behavior_type='cart' THEN user_id END) AS cart_users,
COUNT(DISTINCT CASE WHEN behavior_type='buy' THEN user_id END) AS buy_users,
ROUND(
COUNT(DISTINCT CASE WHEN behavior_type='buy' THEN user_id END)
/COUNT(DISTINCT CASE WHEN behavior_type='pv' THEN user_id END) *100,1
) AS cvr_pct
FROM dwd_user_behavior;
SELECT * FROM ads_funnel;

#ADS 表 2：ads_user_day 日汇总（带环比，给日活折线图做环比）
CREATE TABLE ads_user_day AS
SELECT 
    date, 
    uv, 
    buy_users,
    ROUND( (uv - LAG(uv) OVER (ORDER BY date)) / LAG(uv) OVER (ORDER BY date) *100, 1 ) AS uv_dod_pct
    #LAG()是窗口函数,LAG(uv)：取上一行的 uv 值，2024-11-26 的 LAG (uv) = 2024-11-25 的 uv
#OVER (ORDER BY date)：按照日期从小到大排序，确定 “上一天” 是哪一条，即拿到前一天的日活
#uv_dod_pct：uv 日环比增长率（DOD）
FROM dws_user_day;
SELECT * FROM ads_user_day ORDER BY date;

#ADS 表 3：ads_category 全周期品类汇总（宽口径）
# 修订范围：仅本段；每个品类在DWD全量观察期内对用户分别去重。
# 浏览与购买分别计数，不要求用户交集或行为先后顺序。
# 不累加dws_category_day的日去重人数；日汇总表继续用于每日分析。
# cvr_pct单位为百分数，例如23.4表示23.4%；分母为0时返回NULL。
# 当前项目观察期2024-11-25至12-04；本查询统计DWD当前全部数据。
# 此为建表脚本副本：不会覆盖已有ads_category；已有表请先用另附只读SQL核对。
CREATE TABLE ads_category AS
SELECT
    category_id,
    COUNT(DISTINCT CASE WHEN behavior_type='pv' THEN user_id END) AS view_users,
    COUNT(DISTINCT CASE WHEN behavior_type='buy' THEN user_id END) AS buy_users,
    ROUND(
        100.0 * COUNT(DISTINCT CASE WHEN behavior_type='buy' THEN user_id END)
        / NULLIF(COUNT(DISTINCT CASE WHEN behavior_type='pv' THEN user_id END), 0),
        1
    ) AS cvr_pct
FROM dwd_user_behavior
GROUP BY category_id
ORDER BY buy_users DESC;

SELECT * FROM ads_category;
